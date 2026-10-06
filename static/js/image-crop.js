document.querySelectorAll("[data-image-crop-form]").forEach(form => {
    const fileInput = form.querySelector("[data-crop-file]");
    const preview = form.querySelector("[data-crop-preview]");
    const previewImage = form.querySelector("[data-crop-preview-image]");
    const cropControls = form.querySelector("[data-crop-controls]");
    const xInput = form.querySelector("[data-crop-x]");
    const yInput = form.querySelector("[data-crop-y]");
    const zoomInput = form.querySelector("[data-crop-zoom]");
    let previewUrl;

    const updatePreview = () => {
        if (!previewImage) return;
        previewImage.style.objectPosition =
            `${Number(xInput?.value ?? 0.5) * 100}% ${Number(yInput?.value ?? 0.5) * 100}%`;
        previewImage.style.transform = `scale(${Number(zoomInput?.value ?? 1)})`;
        previewImage.style.transformOrigin =
            `${Number(xInput?.value ?? 0.5) * 100}% ${Number(yInput?.value ?? 0.5) * 100}%`;
    };

    fileInput?.addEventListener("change", () => {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = undefined;
        }
        const file = fileInput.files?.[0];
        if (!file || !file.type.startsWith("image/")) {
            cropControls?.classList.add("d-none");
            preview?.classList.remove("has-image");
            if (previewImage) {
                previewImage.removeAttribute("src");
                previewImage.style.removeProperty("transform");
            }
            return;
        }
        previewUrl = URL.createObjectURL(file);
        previewImage.src = previewUrl;
        preview.classList.add("has-image");
        cropControls?.classList.remove("d-none");
        updatePreview();
    });

    [xInput, yInput, zoomInput].forEach(input =>
        input?.addEventListener("input", updatePreview)
    );
});
