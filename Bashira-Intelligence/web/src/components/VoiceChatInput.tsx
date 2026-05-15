"use client";
import { useState, useRef, useEffect } from "react";
import { ArrowRight, Loader2, Mic, Square, VolumeX } from "lucide-react";

export type VoiceLanguage = "en" | "ar" | "hi";

export interface VoiceSendOptions {
  source?: "text" | "voice";
  displayText?: string;
  replyLanguage?: VoiceLanguage;
  detectedLanguage?: VoiceLanguage;
}

interface VoiceChatInputProps {
  onSendQuery: (query: string, options?: VoiceSendOptions) => void;
  isLoading: boolean;
  voiceLanguage: VoiceLanguage;
  onVoiceLanguageChange: (language: VoiceLanguage) => void;
  isVoicePlaying: boolean;
  onStopVoicePlayback: () => void;
  onVoiceStateChange?: (state: VoiceInputState) => void;
}

export type VoiceInputState = "idle" | "recording" | "transcribing";

const LANGUAGE_COPY: Record<
  VoiceLanguage,
  {
    label: string;
    placeholder: string;
    ready: string;
    listening: string;
    transcribing: string;
    whatToSay: string[];
  }
> = {
  en: {
    label: "ENG",
    placeholder: "Ask in English. Example: Show top delayed rigs this month.",
    ready: "Tap mic to speak. English is the default analysis language.",
    listening: "Recording. Tap again to stop and send.",
    transcribing: "Converting voice to text...",
    whatToSay: [
      "Show top delayed rigs this month",
      "Which projects are at highest risk today",
      "Summarize the latest completion forecast",
    ],
  },
  ar: {
    label: "AR",
    placeholder: "Speak in Arabic. Example: ???? ???????? ?????? ????? ?????.",
    ready: "Arabic voice is supported. The engine will normalize the query for analysis.",
    listening: "Recording Arabic query. Tap again to stop and send.",
    transcribing: "Transcribing Arabic audio...",
    whatToSay: [
      "???? ???????? ?????? ????? ?????",
      "?? ?? ???????? ???????? ??? ?????",
      "??? ?????? ??????? ???????",
    ],
  },
  hi: {
    label: "HIN",
    placeholder: "Hindi me bolo. Example: Is mahine sabse delayed rigs dikhao.",
    ready: "Hindi voice is supported. Query ko analysis ke liye normalize kiya jayega.",
    listening: "Hindi query record ho rahi hai. Dobara tap karke bhejo.",
    transcribing: "Hindi audio ko text me badla ja raha hai...",
    whatToSay: [
      "Is mahine sabse delayed rigs dikhao",
      "Aaj highest risk projects kaun se hain",
      "Latest completion forecast summarize karo",
    ],
  },
};

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/wav",
];

function getRecordingMimeType() {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
    return "";
  }
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

export default function VoiceChatInput({
  onSendQuery,
  isLoading,
  voiceLanguage,
  onVoiceLanguageChange,
  isVoicePlaying,
  onStopVoicePlayback,
  onVoiceStateChange,
}: VoiceChatInputProps) {
  const [query, setQuery] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceInputState>("idle");
  const updateVoiceState = (nextState: VoiceInputState, emit = true) => {
    setVoiceState(nextState);
    if (emit) {
      onVoiceStateChange?.(nextState);
    }
  };
  const [voiceError, setVoiceError] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const transcribeAbortRef = useRef<AbortController | null>(null);

  const copy = LANGUAGE_COPY[voiceLanguage];
  const isRecording = voiceState === "recording";
  const isTranscribing = voiceState === "transcribing";

  useEffect(() => {
    return () => {
      mediaRecorderRef.current?.stop();
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      transcribeAbortRef.current?.abort();
    };
  }, []);

  const transcribeAudio = async (audioBlob: Blob) => {
    const formData = new FormData();
    const extension =
      audioBlob.type === "audio/mp4"
        ? "mp4"
        : audioBlob.type === "audio/wav"
          ? "wav"
          : "webm";
    formData.append("file", audioBlob, `voice-input.${extension}`);
    formData.append("preferred_language", voiceLanguage);

    transcribeAbortRef.current = new AbortController();
    const response = await fetch("/api/voice/stt", {
      method: "POST",
      body: formData,
      signal: transcribeAbortRef.current.signal,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `STT failed with ${response.status}`);
    }

    return response.json() as Promise<{
      transcript?: string;
      normalized_text?: string;
      detected_language?: VoiceLanguage;
      preferred_language?: VoiceLanguage;
    }>;
  };

  const startRecording = async () => {
    setVoiceError("");
    if (isVoicePlaying) {
      onStopVoicePlayback();
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceError("Voice input is not supported in this browser.");
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = getRecordingMimeType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

    mediaStreamRef.current = stream;
    mediaRecorderRef.current = recorder;
    audioChunksRef.current = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunksRef.current.push(event.data);
      }
    };

    recorder.onstop = async () => {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
      audioChunksRef.current = [];
      if (!blob.size) {
        updateVoiceState("idle");
        return;
      }

      updateVoiceState("transcribing");
      let submittedVoiceQuery = false;
      try {
        const payload = await transcribeAudio(blob);
        const transcript = (payload.transcript || "").trim();
        const normalized = (payload.normalized_text || transcript).trim();
        if (!transcript || !normalized) {
          throw new Error("Could not understand speech.");
        }
        setQuery("");
        submittedVoiceQuery = true;
        onSendQuery(normalized, {
          source: "voice",
          displayText: transcript,
          replyLanguage: voiceLanguage,
          detectedLanguage: payload.detected_language || voiceLanguage,
        });
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") {
          setVoiceError("");
        } else {
          setVoiceError(error instanceof Error ? error.message : "Voice query failed.");
        }
      } finally {
        transcribeAbortRef.current = null;
        updateVoiceState("idle", !submittedVoiceQuery);
      }
    };

    recorder.start();
    updateVoiceState("recording");
  };

  const handleVoiceButton = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      return;
    }

    if (isTranscribing) {
      transcribeAbortRef.current?.abort();
      return;
    }

    if (isVoicePlaying) {
      onStopVoicePlayback();
      return;
    }

    try {
      await startRecording();
    } catch (error) {
      updateVoiceState("idle");
      setVoiceError(error instanceof Error ? error.message : "Microphone access failed.");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSendQuery(trimmed, { source: "text", replyLanguage: voiceLanguage });
    setQuery("");
  };

  const helperText = isRecording
    ? copy.listening
    : isTranscribing
      ? copy.transcribing
      : isVoicePlaying
        ? "Voice answer is playing. Tap the button to stop playback."
        : copy.ready;

  const voiceButtonIcon = isRecording ? (
    <Square size={18} strokeWidth={1.8} />
  ) : isTranscribing ? (
    <Loader2 size={18} strokeWidth={1.8} className="animate-spin" />
  ) : isVoicePlaying ? (
    <VolumeX size={18} strokeWidth={1.8} />
  ) : (
    <Mic size={18} strokeWidth={1.8} />
  );

  return (
    <div className="w-full">
      {/* Language Header Removed */}

      <form
        onSubmit={handleSubmit}
        className="flex relative w-full items-end bg-[#FFFFFF] rounded-[28px] px-5 py-4 transition-all duration-300 overflow-hidden group"
        style={{
          fontFamily: '"Figtree", sans-serif',
          boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)",
          border: "1px solid rgba(0,0,0,0.08)",
        }}
      >
        <button
          type="button"
          onClick={handleVoiceButton}
          className={`mr-4 mb-0.5 transition-colors relative z-10 inline-flex h-10 w-10 items-center justify-center rounded-full ${
            isRecording
              ? "bg-[#DC2626] text-white"
              : isTranscribing
                ? "bg-[#FEF3C7] text-[#92400E]"
                : isVoicePlaying
                  ? "bg-[#E5E7EB] text-[#1A1A1A]"
                  : "text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F5F5F5]"
          }`}
          disabled={isLoading && !isVoicePlaying && !isTranscribing}
          title={helperText}
        >
          {voiceButtonIcon}
        </button>

        <textarea
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${e.target.scrollHeight}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          rows={1}
          placeholder={isRecording ? copy.listening : copy.placeholder}
          className="flex-1 bg-transparent outline-none text-[#1A1A1A] placeholder:text-[#9A9A9A] w-full text-[15px] relative z-10 font-medium resize-none overflow-hidden min-h-[22px] max-h-[150px] py-0.5"
          disabled={isLoading || isRecording || isTranscribing}
        />

        <button
          type="submit"
          className="text-[#6B6B6B] hover:text-[#1A1A1A] ms-6 mb-0.5 disabled:opacity-30 transition-colors relative z-10"
          disabled={isLoading || isRecording || isTranscribing || !query.trim()}
        >
          <ArrowRight size={22} strokeWidth={1.6} />
        </button>
      </form>

      {/* Suggested Prompts Removed */}

      <div className="mt-2 px-1">
        <p className={`text-[12px] font-medium ${voiceError ? "text-[#DC2626]" : "text-[#6B6B6B]"}`}>
          {voiceError || helperText}
        </p>
      </div>
    </div>
  );
}
