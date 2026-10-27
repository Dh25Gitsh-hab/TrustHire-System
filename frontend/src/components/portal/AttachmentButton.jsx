/**
 * AttachmentButton — the paperclip. It opens the real file picker.
 *
 * The backend reads TEXT only (it has no file-upload endpoint). So we accept
 * plain-text files (.txt): the browser reads the file on this device and its
 * text is sent with the analysis exactly like pasted text. PDF, Word files and
 * images are NOT uploaded anywhere — the user gets a clear message asking them
 * to copy the text instead.
 */
import { useRef } from 'react'
import { FileText, Paperclip, X } from 'lucide-react'
import Button from '../ui/Button.jsx'
import { formatBytes } from '../../utils/labels.js'

const MAX_FILE_BYTES = 200 * 1024 // 200 KB of text is far more than any job posting

const UNSUPPORTED = [
  { test: /\.pdf$/i, message: 'PDF files cannot be read yet. Open the PDF, copy the job text and paste it here.' },
  { test: /\.(docx?|odt|rtf)$/i, message: 'Word documents cannot be read yet. Open the file, copy the job text and paste it here.' },
  {
    test: /\.(png|jpe?g|gif|webp|heic|bmp)$/i,
    message: 'Screenshots and images cannot be read yet. Copy or type the text from the image and paste it here.',
  },
]

export default function AttachmentButton({ onAttach, onError, disabled }) {
  const inputRef = useRef(null)

  async function handleFileChosen(event) {
    const file = event.target.files?.[0]
    event.target.value = '' // so choosing the same file again still triggers a change
    if (!file) return

    const problem = checkFile(file)
    if (problem) {
      onError(problem)
      return
    }
    try {
      const text = (await file.text()).trim()
      if (!text) {
        onError(`"${file.name}" is empty.`)
        return
      }
      onAttach({ name: file.name, size: file.size, text })
    } catch {
      onError(`"${file.name}" could not be read.`)
    }
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        icon={Paperclip}
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        aria-label="Attach a text file (.txt)"
        title="Attach a text file (.txt, up to 200 KB)"
      />
      <input
        ref={inputRef}
        type="file"
        accept=".txt,text/plain"
        onChange={handleFileChosen}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
      />
    </>
  )
}

function checkFile(file) {
  const unsupported = UNSUPPORTED.find((rule) => rule.test.test(file.name))
  if (unsupported) return unsupported.message
  const isText = /\.txt$/i.test(file.name) || file.type === 'text/plain'
  if (!isText) return 'Only plain-text files (.txt) can be attached. For other files, copy the job text and paste it here.'
  if (file.size > MAX_FILE_BYTES) return `"${file.name}" is too large (${formatBytes(file.size)}). The limit is 200 KB.`
  return null
}

/** The chip shown for an attached file, with a remove button. */
export function AttachmentChip({ attachment, onRemove, disabled }) {
  return (
    <div className="flex max-w-full items-center gap-3 rounded-lg border border-line bg-canvas px-3 py-2 text-sm">
      <FileText className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
      <div className="min-w-0">
        <p className="truncate font-medium text-ink">{attachment.name}</p>
        <p className="text-xs text-ink-muted">
          {formatBytes(attachment.size)} · its text will be included in the analysis
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        icon={X}
        onClick={onRemove}
        disabled={disabled}
        aria-label={`Remove ${attachment.name}`}
        className="ml-auto h-8 w-8"
      />
    </div>
  )
}
