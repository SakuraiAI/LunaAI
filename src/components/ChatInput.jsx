import { useEffect, useRef, useState } from 'react';
import { normalizeTransportText } from '../utils/textRepair';

function MicIcon() {
  return (
    <svg className="input-icon-glyph" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 15.5a3.5 3.5 0 0 0 3.5-3.5V7a3.5 3.5 0 1 0-7 0v5a3.5 3.5 0 0 0 3.5 3.5Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.5 11.5a5.5 5.5 0 0 0 11 0" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M12 17v3.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M9 20.5h6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function VoiceIcon() {
  return (
    <svg className="input-icon-glyph" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 14.5v-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M9.5 17v-10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M13 15.5v-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M16.5 18v-12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M20 13v-2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  onAction,
  attachment,
  onClearAttachment,
  screenShare,
  micRecording = false,
  voiceLoopEnabled = false,
  voiceSpeaking = false,
  centered = false,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const fileInputRef = useRef(null);
  const menuRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;

    function handlePointerDown(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    window.addEventListener('pointerdown', handlePointerDown);
    return () => window.removeEventListener('pointerdown', handlePointerDown);
  }, [menuOpen]);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = '0px';
    const nextHeight = Math.max(30, Math.min(textareaRef.current.scrollHeight, 144));
    textareaRef.current.style.height = `${nextHeight}px`;
  }, [value, attachment?.name, centered]);

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    onAction('file', file);
    setMenuOpen(false);
    event.target.value = '';
  }

  function handleGenerateImage() {
    onAction('image');
    setMenuOpen(false);
  }

  function handleTextChange(event) {
    onChange(normalizeTransportText(event.target.value));
  }

  function handlePaste(event) {
    const pastedText = event.clipboardData?.getData('text');
    if (!pastedText) return;

    const repairedText = normalizeTransportText(pastedText);
    if (repairedText === pastedText) return;

    event.preventDefault();
    const target = event.currentTarget;
    const selectionStart = target.selectionStart ?? value.length;
    const selectionEnd = target.selectionEnd ?? selectionStart;
    const nextValue = `${value.slice(0, selectionStart)}${repairedText}${value.slice(selectionEnd)}`;
    onChange(nextValue);

    window.requestAnimationFrame(() => {
      const caret = selectionStart + repairedText.length;
      target.selectionStart = caret;
      target.selectionEnd = caret;
    });
  }

  function handleKeyDown(event) {
    if (event.isComposing) return;
    if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey) {
      event.preventDefault();
      onSend();
    }
  }

  const isImageAttachment = Boolean(attachment?.previewUrl && attachment?.type?.startsWith('image/'));

  return (
    <div className={`chat-input-shell ${centered ? 'is-centered' : ''}`}>
      <div className="chat-input-plus-zone" ref={menuRef}>
        <button
          className={`input-icon-button ${menuOpen ? 'is-open' : ''}`}
          type="button"
          onClick={() => setMenuOpen((current) => !current)}
          aria-label="Open quick actions"
        >
          +
        </button>
        {menuOpen && (
          <div className="chat-plus-menu">
            <button type="button" onClick={() => fileInputRef.current?.click()}>Add file</button>
            <button type="button" onClick={() => { onAction('share-screen'); setMenuOpen(false); }}>
              {screenShare?.active ? 'Restart desktop share' : 'Share desktop'}
            </button>
            <button type="button" onClick={() => { onAction('speak'); setMenuOpen(false); }}>
              Read aloud once
            </button>
            <button type="button" onClick={handleGenerateImage}>Generate image</button>
          </div>
        )}
        <input ref={fileInputRef} type="file" hidden onChange={handleFileChange} />
      </div>

      <div className="chat-input-main">
        {attachment && (
          <div className={`attachment-chip ${isImageAttachment ? 'is-image' : ''}`}>
            {isImageAttachment && <img src={attachment.previewUrl} alt={attachment.name} className="attachment-preview" />}
            <span>{attachment.name}</span>
            <button type="button" onClick={onClearAttachment} aria-label="Remove attachment">x</button>
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleTextChange}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          placeholder="Message Luna..."
          rows={1}
        />
      </div>
      <button
        className={`input-icon-button ${micRecording ? 'is-recording' : ''}`}
        type="button"
        onClick={() => onAction('mic')}
        aria-label={micRecording ? 'Stop recording' : 'Microphone'}
        title={micRecording ? 'Stop recording and transcribe' : 'Record voice message'}
      >
        <MicIcon />
      </button>
      <button
        className={`input-icon-button input-icon-button-solid ${voiceSpeaking ? 'is-speaking' : ''} ${voiceLoopEnabled ? 'is-voice-loop' : ''}`}
        type="button"
        onClick={() => onAction('voice')}
        aria-label={voiceLoopEnabled ? 'Disable voice loop' : 'Enable voice loop'}
        title={voiceLoopEnabled ? 'Voice loop is active' : 'Enable voice loop'}
      >
        <VoiceIcon />
      </button>
      <button className="send-button" type="button" onClick={() => onSend()}>Send</button>
    </div>
  );
}
