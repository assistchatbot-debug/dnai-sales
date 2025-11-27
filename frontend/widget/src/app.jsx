import { useState, useEffect, useRef } from 'preact/hooks';
import { MessageCircle, X, Send, Mic, Minimize2, Square } from 'lucide-preact';

export function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ id: 1, text: "Здравствуйте! \nЯ могу подсказать как новые технологии могут усилить ваш бизнес. \nЧто вы ищете сегодня?", sender: 'bot' }]);
  const [inputText, setInputText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const toggleChat = () => setIsOpen(!isOpen);
  const scrollToBottom = () => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); };
  
  useEffect(() => { 
    scrollToBottom(); 
    return () => {}; // Cleanup if needed
  }, [messages, isOpen]);

  const [visitorId, setVisitorId] = useState(localStorage.getItem('bizdnaii_vid') || `v_${Math.random().toString(36).substr(2, 9)}`);
  
  useEffect(() => {
    localStorage.setItem('bizdnaii_vid', visitorId);
  }, [visitorId]);

  const getFingerprint = () => ({
    visitorId,
    userAgent: navigator.userAgent,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen: `${window.screen.width}x${window.screen.height}`
  });

  const handleSend = async () => {
    if (!inputText.trim()) return;
    const userMsg = { id: Date.now(), text: inputText, sender: 'user' };
    setMessages(prev => [...prev, userMsg]);
    setInputText("");
    
    // API Call for Text
    try {
        const response = await fetch('/api/sales/1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              message: inputText, 
              session_id: "web-session",
              user_id: visitorId,
              fingerprint: getFingerprint()
            })
        });
        const data = await response.json();
        setMessages(prev => [...prev, { id: Date.now(), text: data.response, sender: 'bot' }]);
    } catch (e) {
        console.error(e);
        setMessages(prev => [...prev, { id: Date.now(), text: "Ошибка связи с сервером.", sender: 'bot' }]);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' });
        await sendVoice(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Не удалось получить доступ к микрофону");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendVoice = async (audioBlob) => {
    setMessages(prev => [...prev, { id: Date.now(), text: "🎤 Отправка голосового...", sender: 'user' }]);
    
    const formData = new FormData();
    formData.append('file', audioBlob, 'voice.webm');
    formData.append('session_id', 'web-session');
    formData.append('user_id', visitorId);
    
    try {
        const response = await fetch('/api/sales/1/voice', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        // Remove "Sending..." message and add real ones
        setMessages(prev => {
            const newMsgs = prev.slice(0, -1);
            newMsgs.push({ id: Date.now(), text: `🗣 Вы сказали: "${data.text}"`, sender: 'user' });
            newMsgs.push({ id: Date.now() + 1, text: data.response, sender: 'bot' });
            return newMsgs;
        });
    } catch (e) {
        console.error(e);
        setMessages(prev => [...prev, { id: Date.now(), text: "Ошибка отправки голоса.", sender: 'bot' }]);
    }
  };

  const handleKeyPress = (e) => { if (e.key === 'Enter') handleSend(); };

  return (
    <div className="fixed bottom-6 right-6 z-[9999] font-sans antialiased text-slate-100">
      {isOpen && (
        <div className="glass mb-4 w-[350px] h-[500px] rounded-2xl flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-bottom-10 fade-in duration-300">
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center"><span className="text-xl">🤖</span></div>
              <div><h3 className="font-bold text-sm">BizDNAii Agent</h3><span className="text-xs text-green-300 flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>Online</span></div>
            </div>
            <button onClick={toggleChat} className="text-white/80 hover:text-white transition"><Minimize2 size={18} /></button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${msg.sender === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'glass-panel text-slate-200 rounded-tl-none'}`}>{msg.text}</div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          <div className="p-4 glass-panel border-t border-white/5">
            <div className="flex items-center gap-2">
              <button 
                className={`p-2 rounded-full transition ${isRecording ? 'bg-red-500 text-white animate-pulse' : 'hover:bg-white/10 text-slate-400'}`} 
                onClick={isRecording ? stopRecording : startRecording}
              >
                {isRecording ? <Square size={20} /> : <Mic size={20} />}
              </button>
              <input type="text" value={inputText} onInput={(e) => setInputText(e.target.value)} onKeyPress={handleKeyPress} placeholder="Напишите сообщение..." className="flex-1 bg-transparent border-none outline-none text-sm text-white placeholder-slate-500" />
              <button onClick={handleSend} className="p-2 bg-indigo-600 hover:bg-indigo-500 rounded-full text-white transition shadow-lg shadow-indigo-500/20"><Send size={18} /></button>
            </div>
          </div>
        </div>
      )}
      <button onClick={toggleChat} className={`w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 ${isOpen ? 'bg-slate-800 text-white rotate-90' : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:scale-110 animate-bounce-slow'}`}>{isOpen ? <X size={24} /> : <MessageCircle size={28} />}</button>
    </div>
  );
}
