import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'

/**
 * Returns Tiptap extensions for the simple rich text profile.
 * Supports: bold, italic, underline, H2/H3, bullet list, ordered list,
 * link, blockquote, undo/redo.
 */
export function getRichTextExtensions() {
  return [
    StarterKit.configure({
      heading: { levels: [2, 3] },
      codeBlock: false,
      code: false,
      horizontalRule: false,
    }),
    Underline,
    Link.configure({
      openOnClick: false,
      autolink: false,
      HTMLAttributes: {
        rel: 'noopener noreferrer',
        target: '_blank',
      },
    }),
  ]
}
