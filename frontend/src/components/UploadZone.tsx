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
    <div className="w-full max-w-md mx-auto lg:ml-auto">
      <div
        className={`upload-zone relative p-6 sm:p-8 text-center cursor-pointer transition-all shadow-[6px_6px_0px_#082F1C] border-3 ${
          dragOver ? "drag-over border-trace-pink" : "border-trace-yellow"
        }`}
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
          <div className="space-y-3">
            <img
              src={preview}
              alt="Uploaded Target"
              className="max-h-48 sm:max-h-56 mx-auto border-2 border-trace-ink object-cover shadow-[3px_3px_0px_#082F1C]"
            />
            <div className="inline-block bg-trace-ink text-trace-cream px-2.5 py-0.5 font-mono text-[11px] border border-trace-yellow/30">
              {file?.name} · {((file?.size || 0) / 1024).toFixed(1)} KB
            </div>
            <p className="font-mono text-[11px] text-trace-yellow underline">
              Click to replace image
            </p>
          </div>
        ) : (
          <div className="space-y-3 py-4">
            <div className="text-4xl text-trace-yellow">⬡</div>
            <p className="font-display font-black text-xl sm:text-2xl text-trace-yellow uppercase tracking-tight">
              DROP TARGET IMAGE
            </p>
            <p className="font-mono text-xs text-trace-cream/80">
              or <span className="underline text-trace-yellow font-bold">CLICK TO BROWSE</span>
            </p>
            <div className="pt-2">
              <span className="inline-block font-mono text-[10px] text-trace-yellow/70 bg-trace-ink px-2 py-0.5 border border-trace-yellow/20 uppercase">
                JPG · PNG · WebP · Single Face
              </span>
            </div>
          </div>
        )}
      </div>

      {file && (
        <motion.button
          className="w-full mt-4 py-3.5 bg-trace-yellow text-trace-ink font-display font-black text-lg sm:text-xl uppercase
                     border-3 border-trace-ink shadow-[5px_5px_0px_#082F1C] hover:bg-trace-pink hover:text-white hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-[2px_2px_0px_#082F1C]
                     transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            onBeginTrace();
          }}
          disabled={disabled}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          BEGIN TRACE →
        </motion.button>
      )}
    </div>
  );
}
