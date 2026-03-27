'use client';
import { useState, useRef, useEffect } from 'react';
import { ArrowRight, Mic, Square } from 'lucide-react';

interface VoiceChatInputProps {
  onSendQuery: (query: string) => void;
  isLoading: boolean;
}

export default function VoiceChatInput({ onSendQuery, isLoading }: VoiceChatInputProps) {
  const [query, setQuery] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const toggleRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          stream.getTracks().forEach((track) => track.stop());

          const formData = new FormData();
          formData.append('file', audioBlob, 'recording.wav');
          
          try {
            const response = await fetch('/api/voice/stt', { method: 'POST', body: formData });
            if (response.ok) {
              const data = await response.json();
              if (data.transcript) {
                setQuery(data.transcript);
              }
            } else {
              console.error("STT Error:", await response.text());
            }
          } catch (error) {
            console.error("STT Request failed:", error);
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Error accessing microphone:", err);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSendQuery(query);
  };

  return (
    <form onSubmit={handleSubmit} className="flex relative w-full items-end bg-[#FFFFFF] rounded-full px-6 py-4 transition-all duration-300 overflow-hidden group" style={{ fontFamily: '"Figtree", sans-serif', boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.08)' }}>

      <button 
        type="button" 
        onClick={toggleRecording} 
        className={`mr-4 mb-0.5 transition-colors relative z-10 ${isRecording ? 'text-[#DC2626] animate-pulse' : 'text-[#6B6B6B] hover:text-[#1A1A1A]'}`}
        disabled={isLoading}
      >
        {isRecording ? <Square size={22} /> : <Mic size={22} strokeWidth={1.5} />}
      </button>

      <textarea
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          e.target.style.height = 'auto';
          e.target.style.height = e.target.scrollHeight + 'px';
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        rows={1}
        placeholder={isRecording ? 'Listening...' : 'Commence inquiry...'}
        className="flex-1 bg-transparent outline-none text-[#1A1A1A] placeholder:text-[#9A9A9A] w-full text-[15px] relative z-10 font-medium resize-none overflow-hidden min-h-[22px] max-h-[150px] py-0.5"
        disabled={isLoading}
      />

      <button type="submit" className="text-[#6B6B6B] hover:text-[#1A1A1A] ms-6 mb-0.5 disabled:opacity-30 transition-colors relative z-10" disabled={isLoading || isRecording || !query.trim()}>
        <ArrowRight size={24} strokeWidth={1.5} />
      </button>
    </form>
  );
}
