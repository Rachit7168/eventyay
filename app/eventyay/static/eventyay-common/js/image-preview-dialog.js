let previewDialog = null;
let previewImage = null;

function getPreviewDialog() {
  if (previewDialog) {
    return previewDialog;
  }

  previewDialog = document.createElement('dialog');
  previewDialog.className = 'eventyay-image-preview-dialog';
  previewDialog.innerHTML =
    '<button type="button" class="eventyay-image-preview-dialog__close" aria-label="Close">&times;</button>' +
    '<img class="eventyay-image-preview-dialog__image" alt="">';

  previewImage = previewDialog.querySelector('.eventyay-image-preview-dialog__image');
  const closeButton = previewDialog.querySelector('.eventyay-image-preview-dialog__close');

  closeButton.addEventListener('click', closeImagePreview);
  previewDialog.addEventListener('click', (event) => {
    if (event.target === previewDialog) {
      closeImagePreview();
    }
  });
  previewDialog.addEventListener('cancel', () => {
    if (previewImage) {
      previewImage.removeAttribute('src');
    }
  });

  document.body.appendChild(previewDialog);
  return previewDialog;
}

function isImagePreviewLink(link) {
  if (!link?.href) {
    return false;
  }

  if (link.matches('[data-lightbox], .thumbnailed-file-preview-container a, a.thumbnailed-file-link, .form-image-preview a')) {
    if (link.querySelector('img')) {
      return true;
    }
    return /\.(jpe?g|png|gif|webp|svg)(\?.*)?$/i.test(link.pathname || link.href);
  }

  return false;
}

export function openImagePreview(url, alt = '') {
  if (!url) {
    return;
  }

  const dialog = getPreviewDialog();
  previewImage.src = url;
  previewImage.alt = alt;
  if (!dialog.open) {
    dialog.showModal();
  }
}

export function closeImagePreview() {
  if (!previewDialog?.open) {
    return;
  }

  previewDialog.close();
  previewImage?.removeAttribute('src');
}

export function initImagePreviewDialog(root = document) {
  root.addEventListener(
    'click',
    (event) => {
      const link = event.target.closest('a');
      if (!isImagePreviewLink(link)) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      const thumb = link.querySelector('img');
      openImagePreview(link.href, thumb?.alt || link.textContent.trim());
    },
    true,
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initImagePreviewDialog());
} else {
  initImagePreviewDialog();
}
