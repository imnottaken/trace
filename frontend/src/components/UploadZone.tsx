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
    <div className="w-full max-w-2xl mx-auto">
      <motion.div
        className={`upload-zone relative p-12 text-center cursor-pointer transition-all ${
          dragOver ? "drag-over border-trace-pink" : "border-trace-yellow"
        } ${preview ? "p-6" : "p-12"}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("file-input")?.click()}
        whileHover={{ scale: 1.01 }}
        transition={{ type: "spring", stiffness: 300 }}
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
              className="max-h-64 mx-auto border-2 border-trace-ink"
            />
            <p className="font-mono text-xs text-trace-cream">
              {file?.name} · {((file?.size || 0) / 1024).toFixed(1)} KB
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-6xl mb-4">⬡</div>
            <p className="font-display font-bold text-2xl text-trace-yellow">
              DROP YOUR IMAGE
            </p>
            <p className="font-mono text-sm text-trace-yellow/60">
              or <span className="underline">CHOOSE FILE</span>
            </p>
          </div>
        )}
      </motion.div>

      {file && (
        <motion.button
          className="w-full mt-6 py-4 bg-trace-yellow text-trace-ink font-display font-bold text-xl
                     border-4 border-trace-ink hover:bg-trace-pink hover:text-white
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={(e) => {
            e.stopPropagation();
            onBeginTrace();
          }}
          disabled={disabled}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          BEGIN TRACE →
        </motion.button>
      )}
    </div>
  );
}
