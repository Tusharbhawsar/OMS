import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import type { UploadResult } from "../types";

interface FileUploadCardProps {
  isUploading: boolean;
  onUpload: (file: File) => Promise<UploadResult | null>;
}

export function FileUploadCard({ isUploading, onUpload }: FileUploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  async function handleSubmit() {
    if (!selectedFile) {
      inputRef.current?.click();
      return;
    }

    const result = await onUpload(selectedFile);
    if (result) {
      setUploadResult(result);
      setSelectedFile(null);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  return (
    <section className="panel upload-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Data Ingestion</p>
          <h2>Upload outage data</h2>
        </div>
        <UploadCloud size={24} />
      </div>

      <div className="upload-box" onClick={() => inputRef.current?.click()} role="button" tabIndex={0}>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
        />
        <strong>{selectedFile ? selectedFile.name : "Choose Excel or CSV file"}</strong>
        <span>Imports customers, service points, outages, mappings, and channel master data.</span>
      </div>

      <button className="primary-button" type="button" disabled={isUploading} onClick={handleSubmit}>
        {isUploading ? "Uploading..." : selectedFile ? "Upload selected file" : "Select file"}
      </button>

      {uploadResult && (
        <div className="upload-result">
          <strong>Imported: {uploadResult.file_name}</strong>
          <ul>
            {Object.entries(uploadResult.imported_tables).map(([table, count]) => (
              <li key={table}>
                {table}: {count}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
