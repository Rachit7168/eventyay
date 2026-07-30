const PREVIEW_LINK_SELECTOR =
  'a[data-lightbox], .thumbnailed-file-preview-container a, a.thumbnailed-file-link, .form-image-preview a';
const IMAGE_EXTENSION = /\.(jpe?g|png|gif|webp|svg)(\?.*)?$/i;

let dialog = null;
let image = null;

function ensureDialog() {
  if (dialog) {
    return;
  }

  dialog = document.createElement('dialog');
  dialog.className = 'eventyay-image-preview-dialog';
  dialog.innerHTML =
    '<button type="button" class="eventyay-image-preview-dialog__close" aria-label="Close">&times;</button>' +
    '<img class="eventyay-image-preview-dialog__image" alt="">';

  image = dialog.querySelector('.eventyay-image-preview-dialog__image');
  dialog.querySelector('.eventyay-image-preview-dialog__close').addEventListener('click', closePreview);
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) {
      closePreview();
    }
  });
  dialog.addEventListener('cancel', () => {
    image.removeAttribute('src');
  });
  document.body.appendChild(dialog);
}

function isImageLink(link) {
  if (!link?.href || !link.matches(PREVIEW_LINK_SELECTOR)) {
    return false;
  }

  if (link.querySelector('img')) {
    return true;
  }

  try {
    return IMAGE_EXTENSION.test(new URL(link.href, window.location.href).pathname);
  } catch {
    return IMAGE_EXTENSION.test(link.href);
  }
}

function openPreview(link) {
  ensureDialog();
  const thumb = link.querySelector('img');
  image.src = link.href;
  image.alt = thumb?.alt || link.textContent.trim();
  if (!dialog.open) {
    dialog.showModal();
  }
}

function closePreview() {
  if (!dialog?.open) {
    return;
  }

  dialog.close();
  image.removeAttribute('src');
}

function handleClick(event) {
  const link = event.target.closest('a');
  if (!isImageLink(link)) {
    return;
  }

  event.preventDefault();
  event.stopImmediatePropagation();
  openPreview(link);
}

function init() {
  document.addEventListener('click', handleClick, true);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
