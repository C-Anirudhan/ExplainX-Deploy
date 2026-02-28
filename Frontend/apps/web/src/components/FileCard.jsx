import React from "react";
import { FileText, Film, Image as ImageIcon, File } from "lucide-react";

const formatSize = (bytes) => {
  if (bytes === 0) return "";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
};

const FileCard = ({ file }) => {
  if (!file) return null;

  let Icon = File;
  const type = (file.type || "").toLowerCase();
  const name = (file.name || "").toLowerCase();

  if (type.includes("pdf") || name.endsWith(".pdf")) {
    Icon = FileText;
  } else if (type.includes("video") || name.match(/\.(mp4|mov|avi|mkv)$/)) {
    Icon = Film;
  } else if (type.includes("image") || name.match(/\.(jpg|jpeg|png|gif|webp)$/)) {
    Icon = ImageIcon;
  }

  return (
    <div className="flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 border border-purple-400/50 shadow-lg max-w-sm w-full transition-transform hover:scale-[1.02]">
      
      {/* Icon Box */}
      <div className="w-12 h-12 flex-shrink-0 flex items-center justify-center bg-black rounded-lg">
        <Icon size={24} className="text-green-400" />
      </div>

      <div className="flex-1 min-w-0 flex flex-col justify-center">
        {/* File Name */}
        <p className="text-base font-bold text-white break-words leading-snug">
          {file.name}
        </p>
        
        {/* Size (Green & New Line) */}
        {file.size > 0 && (
          <p className="text-sm text-green-300 font-bold mt-1">
            {formatSize(file.size)}
          </p>
        )}
      </div>
    </div>
  );
};

export default FileCard;