import React, { useState, useEffect, useRef } from 'react';

// Main App component
const App = () => {
  // State to hold the chat history
  const [chatHistory, setChatHistory] = useState([
    { role: 'model', parts: [{ text: "Who Dat! I'm your go-to source for all things Saints. Ask me anything about the team's history, players, or big games. Let's talk some black and gold!" }] }
  ]);
  // State for the current user input
  const [userInput, setUserInput] = useState('');
  // State to track if an API call is in progress
  const [isLoading, setIsLoading] = useState(false);
  // State for any API-related error messages
  const [apiError, setApiError] = useState(null);

  // A new line was added here.

  // Ref to the chat container for automatic scrolling
  const chatContainerRef = useRef(null);

  // This useEffect hook handles the automatic scrolling to the bottom of the chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, apiError]);

  // Function to send a message to the Gemini API
  const handleSendMessage = async () => {
    // Prevent sending empty messages or multiple requests at once
    if (!userInput.trim() || isLoading) {
      return;
    }

    // Capture the current user message and add it to the chat history
    const userMessage = { role: 'user', parts: [{ text: userInput }] };
    setChatHistory(prevChatHistory => [...prevChatHistory, userMessage]);
    setUserInput(''); // Clear the input field
    setApiError(null); // Reset any previous errors
    setIsLoading(true); // Start loading animation

    try {
      // API call logic with exponential backoff for retries
      const prompt = `You are a chatbot that is a New Orleans Saints superfan. Your persona is enthusiastic and knowledgeable. Respond to user queries about the Saints team's history, players, and big games. User asks: ${userInput}`;
      
      const payload = {
        contents: [{ role: "user", parts: [{ text: prompt }] }],
      };
      
      // IMPORTANT: The API key is now an empty string, allowing the Canvas to provide it at runtime.
      const apiKey = "";
      const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key=${apiKey}`;

      let response;
      let retries = 0;
      const maxRetries = 5;
      const baseDelay = 1000;

      while (retries < maxRetries) {
        try {
          response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (response.ok) {
            break; // Success, exit the loop
          } else {
            retries++;
            const delay = baseDelay * (2 ** retries);
            await new Promise(res => setTimeout(res, delay));
          }
        } catch (error) {
          retries++;
          const delay = baseDelay * (2 ** retries);
          await new Promise(res => setTimeout(res, delay));
        }
      }
      
      if (!response.ok) {
        throw new Error(`Failed to get a response from the API after multiple retries.`);
      }

      const result = await response.json();
      
      // Process the API response and add it to chat history
      if (result.candidates && result.candidates.length > 0 &&
          result.candidates[0].content && result.candidates[0].content.parts &&
          result.candidates[0].content.parts.length > 0) {
        const text = result.candidates[0].content.parts[0].text;
        const botMessage = { role: 'model', parts: [{ text }] };
        setChatHistory(prevChatHistory => [...prevChatHistory, botMessage]);
      } else {
        throw new Error('Unexpected API response format.');
      }
    } catch (error) {
      console.error('Error generating content:', error);
      setApiError("My apologies, there was an issue. Please try again.");
    } finally {
      setIsLoading(false); // Stop loading animation
    }
  };

  // UI for the chatbot using Tailwind CSS for a clean, responsive design
  return (
    <div className="flex flex-col h-screen bg-gray-100 font-inter antialiased">
      {/* Chat container, which is the main scrollable area */}
      <div 
        ref={chatContainerRef} 
        className="flex-1 overflow-y-scroll p-4 space-y-4"
      >
        {chatHistory.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`p-3 max-w-sm md:max-w-md rounded-xl shadow-md ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none'
              }`}
            >
              <p className="text-sm md:text-base">{message.parts[0].text}</p>
            </div>
          </div>
        ))}
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="p-3 rounded-xl shadow-md bg-white text-gray-800 rounded-bl-none">
              <span className="animate-pulse">...</span>
            </div>
          </div>
        )}
        {/* Error message display */}
        {apiError && (
          <div className="flex justify-start">
            <div className="p-3 max-w-sm rounded-xl shadow-md bg-red-100 text-red-700 rounded-bl-none">
              <p className="text-sm">{apiError}</p>
            </div>
          </div>
        )}
      </div>

      {/* Input area at the bottom of the screen */}
      <div className="p-4 bg-white border-t border-gray-200 shadow-lg sticky bottom-0">
        <div className="flex items-center max-w-2xl mx-auto">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            className="flex-1 p-3 rounded-l-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
            placeholder="Ask me about the Saints..."
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            className="p-3 bg-blue-600 text-white rounded-r-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            disabled={isLoading}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Ap