/**
 * BizDNAii Avatar Widget v1.1
 * Fixed: video loading, language in waiting timer
 */
import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
import { X, Send, Mic, Square } from 'lucide-preact';

const VIDEO_BASE = 'https://bizdnai.com/avatar/videos/';
const AUDIO_BASE = 'https://bizdnai.com/avatar/audio/voice/';
const LANG_MAP = { ru: 'ru', en: 'en', kz: 'kz', ky: 'kg', uz: 'uz', uk: 'ua' };

export function App() {
  const [isOpen, setIsOpen] = useState(false);
  const [language, setLanguage] = useState(localStorage.getItem('bizdnaii_widget_lang') || 'ru');
  const langRef = useRef(language); // For closures
  const [visitorId] = useState(localStorage.getItem('bizdnaii_vid') || `v_${Math.random().toString(36).substr(2,9)}`);
  const [companyLogo, setCompanyLogo] = useState('https://bizdnai.com/logo.png');
  const [companyName, setCompanyName] = useState('BizDNAi');
  const [companyId, setCompanyId] = useState(null);
  const [showTooltip, setShowTooltip] = useState(false);
  const [avatarState, setAvatarState] = useState('waiting_blink');
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const audioRef = useRef(null);
  const waitingTimerRef = useRef(null);
  const waitingCountRef = useRef(0);
  const phaseRef = useRef(0);
  
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  
  const texts = {
    ru: { placeholder: 'Сообщение...', error: 'Ошибка', online: 'Online', tooltip: 'Напишите нам...', greeting: 'Привет! Чем помочь?' },
    en: { placeholder: 'Message...', error: 'Error', online: 'Online', tooltip: 'Write to us...', greeting: 'Hello! How can I help?' },
    kz: { placeholder: 'Хабарлама...', error: 'Қате', online: 'Онлайн', tooltip: 'Жазыңыз...', greeting: 'Сәлем! Көмек керек пе?' },
    ky: { placeholder: 'Билдирүү...', error: 'Ката', online: 'Онлайн', tooltip: 'Жазыңыз...', greeting: 'Салам! Жардам керекпи?' },
    uz: { placeholder: 'Xabar...', error: 'Xato', online: 'Onlayn', tooltip: 'Yozing...', greeting: 'Salom! Yordam kerakmi?' },
    uk: { placeholder: 'Повідомлення...', error: 'Помилка', online: 'Онлайн', tooltip: 'Напишіть...', greeting: 'Привіт! Чим допомогти?' }
  };
  const t = texts[language] || texts.ru;

  // Keep langRef in sync
  useEffect(() => { langRef.current = language; }, [language]);

  // Play voice with current language from ref
  const playVoice = useCallback((type, forceLang = null) => {
    const audioLang = LANG_MAP[forceLang || langRef.current] || 'ru';
    const src = `${AUDIO_BASE}${type}_${audioLang}.mp3`;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = src;
      audioRef.current.play().catch(() => {});
    }
  }, []);

  // Waiting timer using langRef
  const startWaitingTimer = useCallback(() => {
    if (waitingTimerRef.current) clearTimeout(waitingTimerRef.current);
    waitingCountRef.current = 0;
    const delays = [10000, 30000, 60000];
    const tick = () => {
      if (waitingCountRef.current >= delays.length) return;
      waitingTimerRef.current = setTimeout(() => {
        playVoice('waiting'); // Uses langRef.current
        waitingCountRef.current++;
        tick();
      }, delays[waitingCountRef.current]);
    };
    tick();
  }, [playVoice]);

  const clearWaitingTimer = () => {
    if (waitingTimerRef.current) {
      clearTimeout(waitingTimerRef.current);
      waitingTimerRef.current = null;
    }
  };

  // Tooltip
  useEffect(() => {
    if (isOpen) { setShowTooltip(false); return; }
    const t1 = setTimeout(() => setShowTooltip(true), 500);
    const t2 = setInterval(() => { setShowTooltip(true); setTimeout(() => setShowTooltip(false), 5000); }, 8000);
    return () => { clearTimeout(t1); clearInterval(t2); };
  }, [isOpen]);

  // Load config
  useEffect(() => {
    localStorage.setItem('bizdnaii_vid', visitorId);
    fetch('https://bizdnai.com/sales/widget/config')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => {
        setCompanyId(d.company_id);
        if (d.logo_url) setCompanyLogo(d.logo_url.startsWith('http') ? d.logo_url : `https://bizdnai.com${d.logo_url}`);
        if (d.company_name) setCompanyName(d.company_name);
        setMessages([{ id: 1, text: d.greetings?.[language] || t.greeting, sender: 'bot' }]);
      })
      .catch(() => setMessages([{ id: 1, text: t.greeting, sender: 'bot' }]));
  }, [language]);

  // Draw video frame
  const drawFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (!video.paused && !video.ended && video.videoWidth > 0) {
      const vw = video.videoWidth, vh = video.videoHeight;
      const cw = canvas.width, ch = canvas.height;
      const scale = Math.max(cw/vw, ch/vh) * (1 + Math.sin(phaseRef.current) * 0.01);
      phaseRef.current += 0.02;
      const w = vw * scale, h = vh * scale;
      const x = (cw - w) / 2, y = (ch - h) / 2;
      
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(video, x, y, w, h);
      
      // Fade edges
      ctx.save();
      ctx.globalCompositeOperation = 'destination-in';
      const g = ctx.createLinearGradient(0, 0, cw, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)');
      g.addColorStop(0.1, 'rgba(255,255,255,1)');
      g.addColorStop(0.9, 'rgba(255,255,255,1)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, cw, ch);
      ctx.restore();
    }
    animationRef.current = requestAnimationFrame(drawFrame);
  }, []);

  // Load video when avatarState changes
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    
    const videos = {
      greeting: 'greeting.mp4',
      waiting_call: 'waiting_call.mp4',
      waiting_blink: 'waiting_blink.mp4',
      thinking: 'thinking.mp4',
      confused: 'confused.mp4',
      speaking: 'speaking.mp4',
      thanking: 'thanking.mp4'
    };
    
    video.src = VIDEO_BASE + (videos[avatarState] || 'waiting_blink.mp4');
    video.loop = ['waiting_blink', 'thinking', 'speaking'].includes(avatarState);
    video.load();
    video.play().catch(() => {});
    
    // Start drawing
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    drawFrame();
    
    // Video ended
    const onEnded = () => {
      if (avatarState === 'greeting') setAvatarState('waiting_call');
      else if (avatarState === 'waiting_call') setAvatarState('waiting_blink');
      else if (['confused', 'thanking'].includes(avatarState)) setAvatarState('waiting_blink');
    };
    video.addEventListener('ended', onEnded);
    
    return () => {
      video.removeEventListener('ended', onEnded);
    };
  }, [avatarState, drawFrame]);

  // Open widget
  const handleOpen = () => {
    setIsOpen(true);
    setAvatarState('greeting');
    setTimeout(() => playVoice('hello'), 100);
    startWaitingTimer();
  };

  // Change language
  const changeLanguage = (newLang) => {
    setLanguage(newLang);
    localStorage.setItem('bizdnaii_widget_lang', newLang);
    clearWaitingTimer();
    setTimeout(() => {
      playVoice('hello', newLang);
      startWaitingTimer();
    }, 100);
  };

  // Send message
  const handleSend = async () => {
    if (!inputText.trim() || !companyId) return;
    const msg = inputText;
    setInputText('');
    setMessages(p => [...p, { id: Date.now(), text: msg, sender: 'user' }]);
    setIsTyping(true);
    setAvatarState('thinking');
    clearWaitingTimer();
    
    try {
      const r = await fetch(`https://bizdnai.com/sales/${companyId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: 'web', user_id: visitorId, language })
      });
      const d = await r.json();
      setMessages(p => [...p, { id: Date.now(), text: d.response, sender: 'bot' }]);
      setAvatarState('speaking');
      setTimeout(() => { setAvatarState('waiting_blink'); startWaitingTimer(); }, 3000);
    } catch {
      setMessages(p => [...p, { id: Date.now(), text: t.error, sender: 'bot', isError: true }]);
      setAvatarState('confused');
    } finally {
      setIsTyping(false);
    }
  };

  // Voice
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = e => chunksRef.current.push(e.data);
      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        sendVoice(blob);
      };
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch {}
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
    setIsRecording(false);
  };

  const sendVoice = async (blob) => {
    if (!companyId) return;
    setMessages(p => [...p, { id: Date.now(), text: '🎤...', sender: 'user' }]);
    setIsTyping(true);
    setAvatarState('thinking');
    const fd = new FormData();
    fd.append('file', blob, 'v.webm');
    fd.append('session_id', 'web');
    fd.append('user_id', visitorId);
    fd.append('language', language);
    try {
      const r = await fetch(`https://bizdnai.com/sales/${companyId}/voice`, { method: 'POST', body: fd });
      const d = await r.json();
      if (d.text) setMessages(p => { const u = [...p]; u[u.length-1] = { id: Date.now(), text: `🗣 ${d.text}`, sender: 'user' }; return u; });
      if (d.response) { setMessages(p => [...p, { id: Date.now(), text: d.response, sender: 'bot' }]); setAvatarState('speaking'); }
    } catch { setMessages(p => [...p, { id: Date.now(), text: t.error, sender: 'bot', isError: true }]); setAvatarState('confused'); }
    finally { setIsTyping(false); setTimeout(() => setAvatarState('waiting_blink'), 3000); }
  };

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const stateLabel = { waiting_blink: 'Ready', greeting: 'Hi!', waiting_call: 'Waiting', thinking: '...', speaking: 'Speaking', confused: '?', thanking: 'Thanks' }[avatarState] || '';

  return (
    <div className="fixed bottom-4 right-6 z-50 font-sans">
      <audio ref={audioRef} />
      
      {isOpen && (
        <div className="mb-4 w-80 bg-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-700" style={{ height: '560px' }}>
          {/* Avatar */}
          <div className="relative bg-gradient-to-b from-slate-900 to-slate-800 p-2">
            <div className="relative w-full flex justify-center" style={{ height: '140px' }}>
              <video ref={videoRef} className="hidden" muted playsInline />
              <canvas ref={canvasRef} width="160" height="140" className="rounded-lg" style={{ background: '#1a1a1a' }} />
              <div className="absolute top-1 right-1 px-2 py-0.5 bg-cyan-500/40 rounded-full text-xs text-white">{stateLabel}</div>
            </div>
            <div className="flex justify-center gap-1 mt-1">
              {['ru','en','kz','ky','uz','uk'].map(l => (
                <button key={l} onClick={() => changeLanguage(l)} className={`px-2 py-0.5 rounded-full text-xs ${language===l ? 'bg-gradient-to-r from-cyan-500 to-purple-500 text-black font-bold' : 'bg-white/10 text-white'}`}>
                  {l==='ru'?'🇷🇺':l==='en'?'🇺🇸':l==='kz'?'🇰🇿':l==='ky'?'🇰🇬':l==='uz'?'🇺🇿':'🇺🇦'}
                </button>
              ))}
            </div>
          </div>
          
          {/* Header */}
          <div className="bg-indigo-600 px-3 py-2 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <img src={companyLogo} className="w-7 h-7 rounded-full" alt="" />
              <div>
                <div className="font-bold text-xs text-white">{companyName}</div>
                <div className="text-xs text-green-300">● {t.online}</div>
              </div>
            </div>
            <button onClick={() => { setIsOpen(false); clearWaitingTimer(); }} className="text-white"><X size={16} /></button>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-2 space-y-2 bg-slate-900/50">
            {messages.map(m => (
              <div key={m.id} className={`flex ${m.sender==='user'?'justify-end':'justify-start'}`}>
                <div className={`max-w-[80%] p-2 rounded-xl text-xs text-white ${m.sender==='user'?'bg-indigo-600':'bg-slate-700'} ${m.isError?'bg-red-500':''}`}>{m.text}</div>
              </div>
            ))}
            {isTyping && <div className="flex justify-start"><div className="bg-slate-700 p-2 rounded-xl flex gap-1"><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"/><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay:'0.2s'}}/><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay:'0.4s'}}/></div></div>}
            <div ref={messagesEndRef}/>
          </div>
          
          {/* Input */}
          <div className="p-2 bg-slate-800 border-t border-slate-700 flex gap-1">
            <input type="text" value={inputText} onInput={e=>setInputText(e.target.value)} onKeyPress={e=>e.key==='Enter'&&handleSend()} placeholder={t.placeholder} className="flex-1 bg-slate-700 text-white rounded-full px-3 py-1.5 text-xs focus:outline-none"/>
            <button onClick={handleSend} className="p-1.5 bg-indigo-600 rounded-full"><Send size={16} className="text-white"/></button>
            <button onPointerDown={e=>{e.preventDefault();startRecording();}} onPointerUp={e=>{e.preventDefault();stopRecording();}} className={`p-1.5 rounded-full ${isRecording?'bg-red-500 animate-pulse':'bg-slate-700'}`} style={{touchAction:'none'}}>{isRecording?<Square size={16} className="text-white"/>:<Mic size={16} className="text-white"/>}</button>
          </div>
        </div>
      )}
      
      {/* Button */}
      <div className="relative">
        <div className={`absolute bottom-full right-0 mb-2 whitespace-nowrap bg-white text-slate-800 px-3 py-1.5 rounded-full shadow-lg text-sm transition-all ${!isOpen&&showTooltip?'opacity-100':'opacity-0 pointer-events-none'}`}>{t.tooltip}</div>
        <button onClick={()=>isOpen?setIsOpen(false):handleOpen()} className="w-14 h-14 rounded-full bg-gradient-to-r from-cyan-500 to-purple-500 flex items-center justify-center shadow-2xl relative">
          {!isOpen&&<span className="absolute inset-0 rounded-full bg-cyan-500 opacity-75 animate-ping"/>}
          <div className="relative z-10">{isOpen?<X size={24} className="text-white"/>:<img src={companyLogo} className="w-7 h-7 rounded-full" alt=""/>}</div>
        </button>
      </div>
      
      <style>{`@keyframes ping{75%,100%{transform:scale(1.8);opacity:0}}`}</style>
    </div>
  );
}
