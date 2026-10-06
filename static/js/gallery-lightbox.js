document.querySelectorAll("[data-gallery-modal]").forEach(modal => {
    modal.addEventListener("show.bs.modal", event => {
        const trigger = event.relatedTarget;
        if (!(trigger instanceof HTMLElement)) return;

        const image = modal.querySelector("[data-gallery-modal-image]");
        const source = trigger.dataset.gallerySrc;
        if (!image || !source) return;

        image.src = source;
        image.alt = trigger.dataset.galleryAlt || "Imagem da galeria";
    });

    modal.addEventListener("hidden.bs.modal", () => {
        const image = modal.querySelector("[data-gallery-modal-image]");
        if (image) image.removeAttribute("src");
    });
});
