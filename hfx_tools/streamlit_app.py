"""Streamlit app for building HFX files from metadata and data folders."""

from __future__ import annotations

import json
import logging
import secrets
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st

from hfx_tools.build import build_hfx_from_folder
from hfx_tools.io import read_hfx_json
from hfx_tools.submission_identity import validate_submission_identity
from hfx_tools.validators import ValidationFramework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _github_oauth_config() -> dict[str, str] | None:
    """Return OAuth settings only when every required secret is configured."""
    try:
        config = st.secrets.get("github_oauth", {})
    except Exception:  # No secrets file is a normal local-development case.
        return None
    required = ("client_id", "client_secret", "redirect_uri")
    if all(config.get(key) for key in required):
        return {key: str(config[key]) for key in required}
    return None


def _github_login(config: dict[str, str], code: str) -> str:
    """Exchange an OAuth code and retrieve the authenticated GitHub login."""
    token_request = Request(
        "https://github.com/login/oauth/access_token",
        data=urlencode({
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": config["redirect_uri"],
        }).encode("utf-8"),
        headers={"Accept": "application/json", "User-Agent": "hfx-tools"},
        method="POST",
    )
    with urlopen(token_request, timeout=10) as response:  # nosec B310: fixed GitHub URL
        token = json.loads(response.read().decode("utf-8")).get("access_token")
    if not token:
        raise ValueError("GitHub did not return an access token")
    user_request = Request(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "hfx-tools"},
    )
    with urlopen(user_request, timeout=10) as response:  # nosec B310: fixed GitHub URL
        login = json.loads(response.read().decode("utf-8")).get("login")
    if not login:
        raise ValueError("GitHub did not return a username")
    return str(login)


def _render_submission_identity_form() -> dict[str, str] | None:
    """Render required contributor fields and return the last valid submission."""
    st.header("Submission identity")
    st.caption(
        "This is bundled as submission metadata; it does not replace scientific producer data."
    )
    config = _github_oauth_config()
    if config:
        params = st.query_params
        code, state = params.get("code"), params.get("state")
        if code and state == st.session_state.get("github_oauth_state"):
            try:
                st.session_state["github_login"] = _github_login(config, code)
                st.success("Signed in with GitHub.")
                st.query_params.clear()
            except Exception as exc:
                st.error(f"GitHub sign-in failed: {exc}")
        elif code:
            st.error("GitHub sign-in could not be verified. Please try again.")

        state = secrets.token_urlsafe(32)
        st.session_state["github_oauth_state"] = state
        auth_url = "https://github.com/login/oauth/authorize?" + urlencode({
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": "read:user",
            "state": state,
        })
        st.link_button("Sign in with GitHub", auth_url)
    else:
        st.caption("GitHub OAuth is not configured; enter a GitHub username below.")

    with st.form("submission_identity_form"):
        name = st.text_input("Contributor name *")
        affiliation = st.text_input("Affiliation *")
        github = st.text_input(
            "GitHub identity / username *",
            value=st.session_state.get("github_login", ""),
        )
        orcid = st.text_input("ORCID (optional)", help="Identifier or https://orcid.org/ URI")
        submitted = st.form_submit_button("Save submission identity")
    if submitted:
        try:
            st.session_state["submission_identity"] = validate_submission_identity({
                "name": name,
                "affiliation": affiliation,
                "github": github,
                "orcid": orcid,
            })
            st.success("Submission identity saved.")
        except ValueError as exc:
            st.session_state.pop("submission_identity", None)
            st.error(str(exc))
    return st.session_state.get("submission_identity")


def _render_hfx_inspector() -> None:
    """Let users browse an existing HFX archive without affecting the build inputs."""
    st.header("Inspect an HFX bundle")
    hfx_file = st.file_uploader("Browse for an .hfx file", type=["hfx"], key="inspect_hfx")
    if not hfx_file:
        return
    try:
        with zipfile.ZipFile(hfx_file) as archive:
            names = archive.namelist()
            if "metadata.json" not in names:
                raise ValueError("The HFX archive does not contain metadata.json")
            metadata = json.loads(archive.read("metadata.json"))
        st.success(f"Archive contains {len(names)} files")
        st.write(names)
        st.subheader("Bundled metadata")
        st.json(metadata)
    except (ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        st.error(f"Could not inspect HFX file: {exc}")


def main():
    st.set_page_config(page_title="HFX Builder", layout="wide")
    st.title("🧬 HFX Builder")
    st.markdown(
        "Build HFX (Haplotype Frequency Exchange) bundles from metadata and data files."
    )
    submission_identity = _render_submission_identity_form()
    _render_hfx_inspector()

    with st.sidebar:
        st.header("Configuration")
        output_name = st.text_input(
            "Output filename",
            value="output",
            help="Name for the output .hfx file (without extension)"
        )
        write_manifest = st.checkbox(
            "Write MANIFEST.json",
            value=True,
            help="Include manifest file in archive"
        )
        hash_alg = st.selectbox(
            "Hash algorithm",
            options=["sha256", "md5", None],
            help="Include checksums in manifest"
        )
        output_dir = st.text_input(
            "Output folder",
            value="output",
            help="Builds are written here rather than into the selected input folder.",
        )

    st.header("Input Folder")
    st.info(
        """
        Expected folder structure:
        ```
        input_folder/
        ├── metadata.json
        └── frequencies.csv  (optional if inline or remote)
        ```
        """
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Option 1: Use Local Folder")
        folder_path = st.text_input(
            "Path to input folder",
            placeholder="/path/to/input_folder"
        )

    with col2:
        st.subheader("Option 2: Upload Files")
        st.info(
            "✨ **Auto-update mode**: Upload your files and the tool will automatically "
            "update `metadata.frequencyLocation` to point to the data file."
        )
        uploaded_metadata = st.file_uploader(
            "Upload metadata.json",
            type=["json"],
            key="metadata_upload"
        )
        uploaded_data = st.file_uploader(
            "Upload frequency data (CSV or Parquet)",
            type=["csv", "parquet"],
            key="data_upload",
            help="Optional: auto-updates metadata.frequencyLocation"
        )

    if folder_path:
        input_folder = Path(folder_path).expanduser()
        local_output_dir = Path(output_dir).expanduser()

        if not input_folder.exists():
            st.error(f"❌ Folder not found: {input_folder}")
            return

        metadata_files = [f for f in input_folder.glob("*.json") if f.name != "MANIFEST.json"]
        if not metadata_files:
            st.error(f"❌ No JSON metadata file found in: {input_folder}")
            return

        st.success(f"✅ Found metadata: {metadata_files[0].name}")

        with st.expander("📋 Metadata Preview"):
            try:
                st.json(read_hfx_json(metadata_files[0]))
            except Exception as e:
                st.error(f"Error reading metadata: {str(e)}")

        if st.button("🔍 Validate", key="validate_btn"):
            try:
                validator = ValidationFramework()
                results = validator.validate(
                    metadata_files[0],
                    read_hfx_json(metadata_files[0]),
                    input_folder
                )
                st.subheader("Validation Results")
                for r in results:
                    if r.level == "error":
                        st.error(f"**{r.validator_name}**: {r.message}")
                    elif r.level == "warning":
                        st.warning(f"**{r.validator_name}**: {r.message}")
                    else:
                        st.info(f"**{r.validator_name}**: {r.message}")
                if not validator.has_errors(results):
                    st.success("✅ All validations passed!")
                else:
                    st.error("❌ Validation failed - fix errors before building")
            except Exception as e:
                st.error(f"Validation error: {str(e)}")

        if st.button("🚀 Build HFX", key="build_btn", disabled=submission_identity is None):
            try:
                with st.spinner("Processing..."):
                    result = build_hfx_from_folder(
                        input_folder=input_folder,
                        output_name=output_name,
                        output_dir=local_output_dir,
                        write_manifest=write_manifest,
                        hash_alg=hash_alg,
                        submission_identity=submission_identity,
                    )

                if result["success"]:
                    st.success(f"✅ HFX created: {result['output_path']}")
                    output_file = Path(result["output_path"])
                    if output_file.exists():
                        with open(output_file, "rb") as f:
                            st.download_button(
                                label="⬇️ Download HFX",
                                data=f.read(),
                                file_name=output_file.name,
                                mime="application/zip"
                            )
                    passed = sum(1 for r in result["validation_results"] if r.passed)
                    total = len(result["validation_results"])
                    st.metric("Validation Results", f"{passed}/{total} passed")
                    if Path(result["log_file"]).exists():
                        with open(result["log_file"]) as f:
                            with st.expander("📝 Build Log"):
                                st.text(f.read())
                else:
                    st.error("❌ Build failed!")
                    for r in result["validation_results"]:
                        if r.level == "error" and not r.passed:
                            st.error(f"  - {r.message}")
                    if "error" in result:
                        st.error(f"Error: {result['error']}")
            except Exception as e:
                st.error(f"Build error: {str(e)}")
                logger.exception("Build failed with exception")

    elif uploaded_metadata:
        st.info("📂 Using uploaded files...")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            metadata_path = tmpdir / "metadata.json"
            metadata_path.write_bytes(uploaded_metadata.getbuffer())

            if uploaded_data:
                (tmpdir / uploaded_data.name).write_bytes(uploaded_data.getbuffer())

            st.subheader("Metadata Preview")
            try:
                metadata = read_hfx_json(metadata_path)
                if uploaded_data:
                    st.info(
                        f"📝 **Will be updated**: `metadata.frequencyLocation` → "
                        f"`file://{uploaded_data.name}`"
                    )
                st.json(metadata)
            except Exception as e:
                st.error(f"Error reading metadata: {str(e)}")
                return

            if st.button(
                "🚀 Build HFX", key="build_btn_upload", disabled=submission_identity is None
            ):
                try:
                    with st.spinner("Processing..."):
                        result = build_hfx_from_folder(
                            input_folder=tmpdir,
                            output_name=output_name,
                            output_dir=tmpdir,
                            write_manifest=write_manifest,
                            hash_alg=hash_alg,
                            submission_identity=submission_identity,
                        )
                    if result["success"]:
                        st.success("✅ HFX created successfully!")
                        output_file = Path(result["output_path"])
                        if output_file.exists():
                            with open(output_file, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download HFX",
                                    data=f.read(),
                                    file_name=output_file.name,
                                    mime="application/zip"
                                )
                    else:
                        st.error("❌ Build failed!")
                except Exception as e:
                    st.error(f"Build error: {str(e)}")

    else:
        st.info("👈 Enter a folder path or upload files to get started")


if __name__ == "__main__":
    main()
