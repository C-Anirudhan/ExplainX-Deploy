import { useEffect, useRef } from "react";
import useChatStore from "@/store/chatStore";
import ChatMessage from "@/components/ChatMessage";
import FileCard from "@/components/FileCard"; // 1. Import FileCard
import { Loader2 } from "lucide-react";

export default function ChatWindow() {
  const { messages, isTyping } = useChatStore();
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-4" // Increased space-y for better card separation
      style={{ scrollBehavior: "smooth" }}
    >
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-4">
            <div className="text-6xl">🤖</div>
            <h2 className="text-2xl font-bold text-white">
              Welcome to ExplainX
            </h2>
            <p className="text-gray-400 max-w-md">
              Upload videos, PDFs, PPTs, or documents and ask questions. I'll
              analyze them using AI and provide detailed explanations.
            </p>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message, index) => {
            // ----------------------------------------------------
            // 2. LOGIC TO DETECT FILES (New & Old Legacy Text)
            // ----------------------------------------------------
            let fileData = message.file;

            // Handle old "Uploaded: file.pdf" messages that don't have file metadata
            if (!fileData && message.role === "user" && typeof message.content === "string" && message.content.startsWith("Uploaded:")) {
              const filename = message.content.replace("Uploaded:", "").trim();
              fileData = {
                name: filename,
                size: 0, 
                type: filename.endsWith(".pdf") ? "application/pdf" : "video/mp4"
              };
            }

            // ----------------------------------------------------
            // 3. RENDER FILE CARD OR NORMAL MESSAGE
            // ----------------------------------------------------
            if (fileData) {
              return (
                <div key={index} className="flex justify-end px-2">
                   {/* We wrap it in a div to align it to the right (User side) */}
                   <FileCard file={fileData} />
                </div>
              );
            }

            return <ChatMessage key={index} message={message} />;
          })}

          {isTyping && (
            <div className="flex gap-4 p-4 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Loader2 size={18} className="text-white animate-spin" />
              </div>
              <div className="bg-gray-800 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}