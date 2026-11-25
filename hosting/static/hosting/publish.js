const form = document.querySelector("[data-publish-form]");

if (form) {
  const input = form.querySelector('input[type="file"]');
  const dropArea = form.querySelector("[data-drop-area]");
  const button = form.querySelector("[data-publish-button]");
  const label = form.querySelector("[data-publish-label]");
  const status = form.querySelector("[data-publish-status]");

  const reset = () => {
    button.disabled = false;
    form.classList.remove("is-publishing");
    label.textContent = "Publish site";
    status.textContent = "";
  };

  input.accept = ".zip,application/zip";
  dropArea.addEventListener("dragover", (event) => {
    if (event.dataTransfer.types.includes("Files")) {
      event.preventDefault();
      dropArea.classList.add("is-over");
    }
  });
  dropArea.addEventListener("dragleave", (event) => {
    if (!dropArea.contains(event.relatedTarget)) dropArea.classList.remove("is-over");
  });
  dropArea.addEventListener("drop", (event) => {
    event.preventDefault();
    dropArea.classList.remove("is-over");
    if (button.disabled) return;

    const files = event.dataTransfer.files;
    if (files.length !== 1 || !files[0].name.toLowerCase().endsWith(".zip")) {
      status.textContent = "Drop one ZIP file.";
      return;
    }
    input.files = files;
    status.textContent = "";
  });
  input.addEventListener("change", () => { status.textContent = ""; });
  form.addEventListener("submit", () => {
    button.disabled = true;
    form.classList.add("is-publishing");
    label.textContent = "Publishing…";
    status.textContent = "Uploading and checking your ZIP.";
  });
  window.addEventListener("pageshow", reset);
}

const copyButton = document.querySelector("[data-copy-url]");

if (copyButton && navigator.clipboard) {
  copyButton.hidden = false;
  copyButton.addEventListener("click", async () => {
    const status = document.querySelector("[data-copy-status]");
    try {
      await navigator.clipboard.writeText(copyButton.dataset.copyUrl);
      copyButton.textContent = "Copied";
      status.textContent = "Link copied.";
    } catch {
      status.textContent = "Copy failed. Select the site URL to copy it.";
      copyButton.textContent = "Copy failed";
    }
  });
}
