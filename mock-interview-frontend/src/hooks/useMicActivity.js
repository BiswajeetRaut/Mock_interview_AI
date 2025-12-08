import { useEffect, useRef, useState } from "react";

export default function useMicActivity(micOn) {
    const [isSpeaking, setIsSpeaking] = useState(false);

    const micRef = useRef(micOn);
    const rafRef = useRef(null);

    useEffect(() => {
        micRef.current = micOn; // keep ref updated
    }, [micOn]);

    useEffect(() => {
        let stream = null;
        let audioContext = null;
        let analyser = null;
        let dataArray = null;

        const stopAudio = () => {
            console.log("🛑 Stopping audio...");

            if (rafRef.current) cancelAnimationFrame(rafRef.current);

            if (stream) {
                stream.getTracks().forEach((t) => t.stop());
                console.log("🎤 Mic stream stopped");
            }
            if (audioContext) {
                audioContext.close();
                console.log("🎧 AudioContext closed");
            }
            setIsSpeaking(false);
        };

        if (!micOn) {
            stopAudio();
            return;
        }

        const setup = async () => {
            try {
                console.log("🎤 Requesting mic...");
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });

                audioContext = new AudioContext();
                const source = audioContext.createMediaStreamSource(stream);

                analyser = audioContext.createAnalyser();
                analyser.fftSize = 256;

                dataArray = new Uint8Array(analyser.frequencyBinCount);
                source.connect(analyser);

                console.log("🎧 Analyzer ready");

                const detect = () => {
                    if (!micRef.current) {
                        console.log("❌ Mic off detected. Stopping loop.");
                        stopAudio();
                        return;
                    }

                    analyser.getByteFrequencyData(dataArray);
                    const volume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

                    console.log("🔊 Volume:", volume);

                    setIsSpeaking(volume > 18);

                    rafRef.current = requestAnimationFrame(detect);
                };

                detect();
            } catch (e) {
                console.error("❌ Mic error:", e);
            }
        };

        setup();

        return () => {
            stopAudio();
        };
    }, [micOn]);

    return isSpeaking;
}
