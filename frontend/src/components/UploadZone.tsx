"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  onBeginTrace: () => void;
  disabled?: boolean;
}

export default function UploadZone({ onFileSelect, onBeginTrace, disabled }: UploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    (f: File) => {
      if (!f.type.startsWith("image/")) return;
      setFile(f);
      setPreview(URL.createObjectURL(f));
      onFileSelect(f);
    },
    [onFileSelect]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  return (
    <div className="w-full max-w-2xl">
      <div
        className={`upload-zone relative p-8 sm:p-12 text-center cursor-pointer transition-all shadow-[6px_6px_0px_#082F1C] ${
          dragOver ? "drag-over border-trace-pink" : "border-trace-yellow"
        } ${preview ? "p-6" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept="image/*"
          className="hidden"
          onChange={onInputChange}
        />

        {preview ? (
          <div className="space-y-4">
            <img
              src={preview}
              alt="Uploaded"
              className="max-h-72 mx-auto border-3 border-trace-ink shadow-[4px_4px_0px_#082F1C]"
            />
            <div className="inline-block bg-trace-ink text-trace-cream px-3 py-1 font-mono text-xs border border-trace-yellow/30">
              {file?.name} · {((file?.size || 0) / 1024).toFixed(1)} KB
            </div>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            <div className="text-5xl text-trace-yellow">⬡</div>
            <p className="font-display font-bold text-2xl sm:text-3xl text-trace-yellow uppercase tracking-tight">
              DROP TARGET IMAGE
            </p>
            <p className="font-mono text-xs sm:text-sm text-trace-cream/70">
              or <span className="underline text-trace-yellow font-bold">CLICK TO BROWSE</span>
            </p>
            <p className="font-mono text-[11px] text-trace-cream/50 uppercase tracking-wider mt-4">
              Supports JPG, PNG, WebP · Single Face Portrait Recommended
            </p>
          </div>
        )}
      </div>

      {file && (
        <motion.button
          className="w-full mt-6 py-4 bg-trace-yellow text-trace-ink font-display font-black text-xl sm:text-2xl uppercase
                     border-3 border-trace-ink shadow-[6px_6px_0px_#082F1C] hover:bg-trace-pink hover:text-white hover:translate-x-1 hover:translate-y-1 hover:shadow-[3px_3px_0px_#082F1C]
                     transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            onBeginTrace();
          }}
          disabled={disabled}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
        >
          BEGIN TRACE →
        </motion.button>
      )}
    </div>
  );
}
