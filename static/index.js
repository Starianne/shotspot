const pinpointButton = document.getElementById("pinpoint");

const imageUrls = [
    "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1200&q=80",
];

function createImagePopup() {
    const popup = document.createElement("div");
    popup.className = "image-popup";
    popup.setAttribute("role", "dialog");
    popup.setAttribute("aria-modal", "true");
    popup.setAttribute("aria-labelledby", "image-popup-title");

    const content = document.createElement("div");
    content.className = "image-popup__content";

    const closeButton = document.createElement("button");
    closeButton.className = "image-popup__close";
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close images");
    closeButton.textContent = "×";

    const title = document.createElement("h2");
    title.id = "image-popup-title";
    title.textContent = "Photos at this location";

    const images = document.createElement("div");
    images.className = "image-popup__images";

    imageUrls.forEach((url, index) => {
        const image = document.createElement("img");
        image.src = url;
        image.alt = `Photo ${index + 1} from this location`;
        image.loading = "lazy";
        images.appendChild(image);
    });

    const closePopup = () => popup.remove();
    closeButton.addEventListener("click", closePopup);
    popup.addEventListener("click", (event) => {
        if (event.target === popup) {
            closePopup();
        }
    });

    content.append(closeButton, title, images);
    popup.appendChild(content);
    document.body.appendChild(popup);
    closeButton.focus();
}

pinpointButton.addEventListener("click", createImagePopup);