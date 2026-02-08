import { useCallback, useEffect, useRef, useState } from "react";

interface ConversationAudioState {
  isPlaying: boolean;
  currentProvider: { id: string; name: string } | null;
  error: string | null;
}

interface UseConversationAudioReturn extends ConversationAudioState {
  playAudioChunk: (audioBase64: string, providerId: string, providerName: string) => Promise<void>;
  setCurrentProvider: (provider: { id: string; name: string } | null) => void;
  reset: () => void;
}

/**
 * Hook to manage conversation audio playback using Web Audio API.
 *
 * Decodes base64 PCM audio chunks and plays them smoothly in sequence.
 * Designed for real-time streaming of ElevenLabs agent conversations.
 */
export function useConversationAudio(): UseConversationAudioReturn {
  const [state, setState] = useState<ConversationAudioState>({
    isPlaying: false,
    currentProvider: null,
    error: null,
  });

  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const nextStartTimeRef = useRef(0);

  // Initialize AudioContext on first use
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      // Create AudioContext with 16kHz sample rate to match ElevenLabs
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });
    }
    return audioContextRef.current;
  }, []);

  // Decode base64 audio to ArrayBuffer
  const decodeBase64Audio = useCallback((base64: string): ArrayBuffer => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }, []);

  // Convert PCM bytes to AudioBuffer
  const pcmToAudioBuffer = useCallback(async (
    pcmData: ArrayBuffer,
    sampleRate: number = 16000
  ): Promise<AudioBuffer> => {
    const audioContext = getAudioContext();

    // PCM is raw 16-bit signed integer samples
    const pcmView = new Int16Array(pcmData);
    const floatSamples = new Float32Array(pcmView.length);

    // Convert Int16 to Float32 (-1.0 to 1.0)
    for (let i = 0; i < pcmView.length; i++) {
      floatSamples[i] = pcmView[i] / 32768.0;
    }

    // Create AudioBuffer
    const audioBuffer = audioContext.createBuffer(1, floatSamples.length, sampleRate);
    audioBuffer.copyToChannel(floatSamples, 0);

    return audioBuffer;
  }, [getAudioContext]);

  // Play queued audio buffers
  const playQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;
    setState(prev => ({ ...prev, isPlaying: true, error: null }));

    const audioContext = getAudioContext();
    const currentTime = audioContext.currentTime;

    // Reset start time if we've fallen behind
    if (nextStartTimeRef.current < currentTime) {
      nextStartTimeRef.current = currentTime;
    }

    while (audioQueueRef.current.length > 0) {
      const buffer = audioQueueRef.current.shift();
      if (!buffer) continue;

      const source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContext.destination);

      source.start(nextStartTimeRef.current);
      nextStartTimeRef.current += buffer.duration;
    }

    // Wait for playback to finish
    const waitTime = (nextStartTimeRef.current - audioContext.currentTime) * 1000;
    if (waitTime > 0) {
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }

    isPlayingRef.current = false;
    setState(prev => ({ ...prev, isPlaying: false }));
  }, [getAudioContext]);

  // Public API: Play an audio chunk
  const playAudioChunk = useCallback(async (
    audioBase64: string,
    providerId: string,
    providerName: string
  ) => {
    try {
      // Decode and convert to AudioBuffer
      const arrayBuffer = decodeBase64Audio(audioBase64);
      const audioBuffer = await pcmToAudioBuffer(arrayBuffer);

      // Add to queue
      audioQueueRef.current.push(audioBuffer);

      // Update current provider if different
      setState(prev => {
        if (prev.currentProvider?.id !== providerId) {
          return {
            ...prev,
            currentProvider: { id: providerId, name: providerName },
            error: null,
          };
        }
        return { ...prev, error: null };
      });

      // Start playing if not already
      await playQueue();
    } catch (error) {
      console.error("Error playing audio chunk:", error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : "Failed to play audio",
      }));
    }
  }, [decodeBase64Audio, pcmToAudioBuffer, playQueue]);

  // Public API: Set current provider (for conversation_started)
  const setCurrentProvider = useCallback((provider: { id: string; name: string } | null) => {
    setState(prev => ({ ...prev, currentProvider: provider }));
  }, []);

  // Public API: Reset state (for conversation_ended)
  const reset = useCallback(() => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    nextStartTimeRef.current = 0;
    setState({
      isPlaying: false,
      currentProvider: null,
      error: null,
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  return {
    ...state,
    playAudioChunk,
    setCurrentProvider,
    reset,
  };
}
