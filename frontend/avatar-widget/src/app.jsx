/**
 * BizDNAii Avatar Widget v2.0
 * Video preview instead of button
 */
import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
import { X, Send, Mic, Square } from 'lucide-preact';

const VIDEO_BASE = 'https://bizdnai.com/avatar/videos/';
const AUDIO_BASE = 'https://bizdnai.com/avatar/audio/voice/';
const LANG_MAP = { ru: 'ru', en: 'en', kz: 'kz', ky: 'kg', uz: 'uz', uk: 'ua' };
const LANG_LABELS = { ru: '🇷🇺 Русский', en: '🇺🇸 English', kz: '🇰🇿 Қазақша', ky: '🇰🇬 Кыргызча', uz: '🇺🇿 O\'zbekcha', uk: '🇺🇦 Українська' };

export function App() {
  
  const [isOpen, setIsOpen] = useState(false);
  

  const [language, setLanguage] = useState(localStorage.getItem('bizdnaii_widget_lang') || 'ru');
  const langRef = useRef(language);
  const [visitorId] = useState(localStorage.getItem('bizdnaii_vid') || `v_${Math.random().toString(36).substr(2,9)}`);
  const [companyLogo, setCompanyLogo] = useState('https://bizdnai.com/logo.png');
  const [companyName, setCompanyName] = useState('BizDNAi');
  const [companyId, setCompanyId] = useState(null);
  const [avatarState, setAvatarState] = useState('waiting_blink');
  
  // Preview video refs (for closed state)
  const previewVideoRef = useRef(null);
  const previewCanvasRef = useRef(null);
  const previewAnimRef = useRef(null);
  
  // Main video refs (for open state)
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  
  const audioRef = useRef(null);
  const waitingTimerRef = useRef(null);
  const waitingCountRef = useRef(0);
  const userStartedChatRef = useRef(false);
  const phaseRef = useRef(0);
  
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [userStartedChat, setUserStartedChat] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  
  const texts = {
    ru: { placeholder: 'Сообщение...', error: 'Ошибка сервера', online: 'Online', greeting: 'Привет! Чем помочь?', push: 'Нажмите' },
    en: { placeholder: 'Message...', error: 'Server error', online: 'Online', greeting: 'Hello! How can I help?', push: 'Push' },
    kz: { placeholder: 'Хабарлама...', error: 'Сервер қатесі', online: 'Онлайн', greeting: 'Сәлем! Көмек керек пе?', push: 'Басыңыз' },
    ky: { placeholder: 'Билдирүү...', error: 'Сервер катасы', online: 'Онлайн', greeting: 'Салам! Жардам керекпи?', push: 'Басыңыз' },
    uz: { placeholder: 'Xabar...', error: 'Server xatosi', online: 'Onlayn', greeting: 'Salom! Yordam kerakmi?', push: 'Bosing' },
    uk: { placeholder: 'Повідомлення...', error: 'Помилка сервера', online: 'Онлайн', greeting: 'Привіт! Чим допомогти?', push: 'Натисніть' }
  };
  const t = texts[language] || texts.ru;

  const stateLabels = {
    ru: { waiting_blink: 'Готов', greeting: 'Приветствую', waiting_call: 'Жду', thinking: 'Думаю...', speaking: 'Говорю', confused: 'Не понял', thanking: 'Спасибо!' },
    en: { waiting_blink: 'Ready', greeting: 'Hello', waiting_call: 'Waiting', thinking: 'Thinking...', speaking: 'Speaking', confused: 'Confused', thanking: 'Thanks!' },
    kz: { waiting_blink: 'Дайын', greeting: 'Сәлем', waiting_call: 'Күтемін', thinking: 'Ойланамын...', speaking: 'Айтамын', confused: 'Түсінбедім', thanking: 'Рахмет!' },
    ky: { waiting_blink: 'Даяр', greeting: 'Салам', waiting_call: 'Күтөм', thinking: 'Ойлонууда...', speaking: 'Айтып жатам', confused: 'Түшүнбөдүм', thanking: 'Рахмат!' },
    uz: { waiting_blink: 'Tayyor', greeting: 'Salom', waiting_call: 'Kutmoqda', thinking: "O'ylayapman...", speaking: 'Gapiryapman', confused: 'Tushunmadim', thanking: 'Rahmat!' },
    uk: { waiting_blink: 'Готовий', greeting: 'Вітаю', waiting_call: 'Чекаю', thinking: 'Думаю...', speaking: 'Говорю', confused: 'Не зрозумів', thanking: 'Дякую!' }
  };

  useEffect(() => { langRef.current = language; }, [language]);
  useEffect(() => { userStartedChatRef.current = userStartedChat; }, [userStartedChat]);

  const playVoice = useCallback((type, forceLang = null) => {
    const audioLang = LANG_MAP[forceLang || langRef.current] || 'ru';
    const src = `${AUDIO_BASE}${type}_${audioLang}.mp3`;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = src;
      audioRef.current.play().catch(() => {});
    }
  }, []);

  const startWaitingTimer = useCallback(() => {
    if (waitingTimerRef.current) clearTimeout(waitingTimerRef.current);
    waitingCountRef.current = 0;
    const delays = [10000, 30000, 60000];
    const tick = () => {
      if (waitingCountRef.current >= delays.length) return;
      waitingTimerRef.current = setTimeout(() => {
        if (!userStartedChatRef.current) playVoice('waiting');
        waitingCountRef.current++;
        tick();
      }, delays[waitingCountRef.current]);
    };
    tick();
  }, [playVoice]);

  const clearWaitingTimer = () => {
    if (waitingTimerRef.current) { clearTimeout(waitingTimerRef.current); waitingTimerRef.current = null; }
  };

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

  // Draw frame helper
  const drawVideoFrame = (video, canvas, anim, phase) => {
    if (!video || !canvas) return;
    const ctx = canvas.getContext('2d');
    
    if (!video.paused && !video.ended && video.videoWidth > 0) {
      const vw = video.videoWidth, vh = video.videoHeight;
      const cw = canvas.width, ch = canvas.height;
      const scale = Math.max(cw/vw, ch/vh) * (1 + Math.sin(phase.current) * 0.01);
      phase.current += 0.02;
      const w = vw * scale, h = vh * scale;
      const x = (cw - w) / 2, y = (ch - h) / 2;
      
      ctx.clearRect(0, 0, cw, ch);
      ctx.drawImage(video, x, y, w, h);
      
      // Fade edges
      ctx.save();
      ctx.globalCompositeOperation = 'destination-in';
      const g = ctx.createLinearGradient(0, 0, cw, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)');
      g.addColorStop(0.08, 'rgba(255,255,255,1)');
      g.addColorStop(0.92, 'rgba(255,255,255,1)');
      g.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, cw, ch);
      ctx.restore();
    }
    anim.current = requestAnimationFrame(() => drawVideoFrame(video, canvas, anim, phase));
  };

  // Preview video (always playing when closed)
  useEffect(() => {
    if (isOpen) {
      if (previewAnimRef.current) cancelAnimationFrame(previewAnimRef.current);
      return;
    }
    const video = previewVideoRef.current;
    const canvas = previewCanvasRef.current;
    if (!video || !canvas) return;
    
    video.src = VIDEO_BASE + 'waiting_blink.mp4';
    video.loop = true;
    video.load();
    video.play().catch(() => {});
    
    const phase = { current: 0 };
    const draw = () => {
      drawVideoFrame(video, canvas, previewAnimRef, phase);
    };
    video.addEventListener('loadeddata', draw);
    
    return () => {
      if (previewAnimRef.current) cancelAnimationFrame(previewAnimRef.current);
    };
  }, [isOpen]);

  // Main video (when open)
  useEffect(() => {
    if (!isOpen) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    
    const videos = { greeting: 'greeting.mp4', waiting_call: 'waiting_call.mp4', waiting_blink: 'waiting_blink.mp4', thinking: 'thinking.mp4', confused: 'confused.mp4', speaking: 'speaking.mp4', thanking: 'thanking.mp4' };
    
    video.src = VIDEO_BASE + (videos[avatarState] || 'waiting_blink.mp4');
    video.loop = ['waiting_blink', 'thinking', 'speaking'].includes(avatarState);
    video.load();
    video.play().catch(() => {});
    
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    const phase = { current: phaseRef.current };
    const draw = () => drawVideoFrame(video, canvas, animationRef, phase);
    video.addEventListener('loadeddata', draw);
    
    const onEnded = () => {
      if (avatarState === 'greeting') setAvatarState('waiting_call');
      else if (avatarState === 'waiting_call') setAvatarState('waiting_blink');
      else if (['confused', 'thanking'].includes(avatarState)) setAvatarState('waiting_blink');
    };
    video.addEventListener('ended', onEnded);
    
    return () => {
      video.removeEventListener('ended', onEnded);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isOpen, avatarState]);

  const handleOpen = () => {
    setIsOpen(true);
    setAvatarState('waiting_blink');
    setTimeout(() => {
      setAvatarState('greeting');
      playVoice('hello');
      startWaitingTimer();
    }, 50);
  };

  const changeLanguage = (newLang) => {
    setLanguage(newLang);
    localStorage.setItem('bizdnaii_widget_lang', newLang);
    clearWaitingTimer();
    setTimeout(() => { playVoice('hello', newLang); startWaitingTimer(); }, 100);
  };

  const handleSend = async () => {
    if (!inputText.trim() || !companyId) return;
    const msg = inputText;
    setInputText('');
    setMessages(p => [...p, { id: Date.now(), text: msg, sender: 'user' }]);
    setIsTyping(true);
    setAvatarState('thinking');
    setUserStartedChat(true);
    clearWaitingTimer();
    
    try {
      const r = await fetch(`https://bizdnai.com/sales/${companyId}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, session_id: 'web', user_id: visitorId, language })
      });
      const d = await r.json();
      setMessages(p => [...p, { id: Date.now(), text: d.response, sender: 'bot' }]);
      setAvatarState('speaking');
      setTimeout(() => { setAvatarState('waiting_blink'); startWaitingTimer(); }, 3000);
    } catch {
      setMessages(p => [...p, { id: Date.now(), text: t.error, sender: 'bot', isError: true }]);
      setAvatarState('confused');
    } finally { setIsTyping(false); }
  };

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

  const getStateLabel = () => (stateLabels[language] || stateLabels.ru)[avatarState] || avatarState;

  return (
    <div className="fixed bottom-4 right-4 z-50 font-sans">
      <audio ref={audioRef} />
      
      {isOpen ? (
        <div style={{ width: 'min(90vw, 420px)', height: 'min(85vh, 750px)', marginBottom: '16px' }} className="bg-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-slate-700 widget-open">
          {/* Avatar with close button */}
          <div className="relative bg-gradient-to-b from-slate-900 to-slate-800">
            {/* Close button top right */}
            <button onClick={() => { setIsOpen(false); clearWaitingTimer(); }} className="absolute top-2 right-2 z-10 text-white hover:bg-white/20 p-1.5 rounded-full bg-black/30"><X size={18} /></button>
            
            <div className="relative w-full flex justify-center" style={{ height: '265px' }}>
              <video ref={videoRef} className="hidden" muted playsInline />
              <canvas ref={canvasRef} width="220" height="265" className="rounded-lg" style={{ background: '#1a1a1a' }} />
              {/* Status left side */}
              <div className="absolute top-2 left-2 px-2 py-1 bg-cyan-500/40 backdrop-blur rounded-full text-xs text-white font-medium">{getStateLabel()}</div>
            </div>
          </div>
          
          {/* Header */}
          <div className="bg-indigo-600 px-4 py-3 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <img src={companyLogo} className="w-10 h-10 rounded-full" alt="" />
              <div>
                <div className="font-bold text-sm text-white">{companyName}</div>
                <div className="text-xs text-green-300">● {t.online}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <select value={language} onChange={(e) => changeLanguage(e.target.value)} className="bg-indigo-500/30 border border-indigo-400/40 text-white text-sm rounded-lg px-2 py-1 focus:outline-none cursor-pointer">
                {Object.entries(LANG_LABELS).map(([code, label]) => (<option key={code} value={code}>{label}</option>))}
              </select>

            </div>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-900/50">
            {messages.map(m => (
              <div key={m.id} className={`flex ${m.sender==='user'?'justify-end':'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-2xl text-sm whitespace-pre-line text-white ${m.sender==='user'?'bg-indigo-600':'bg-slate-700'} ${m.isError?'bg-red-500':''}`}>{m.text}</div>
              </div>
            ))}
            {isTyping && (<div className="flex justify-start"><div className="bg-slate-700 p-4 rounded-2xl flex gap-1"><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"/><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay:'0.2s'}}/><div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay:'0.4s'}}/></div></div>)}
            <div ref={messagesEndRef}/>
          </div>
          
          {/* Input */}
          <div className="p-3 bg-slate-800 border-t border-slate-700 flex gap-2">
            <input type="text" value={inputText} onInput={e=>setInputText(e.target.value)} onKeyPress={e=>e.key==='Enter'&&handleSend()} placeholder={t.placeholder} className="flex-1 bg-slate-700 text-white rounded-full px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            <button onClick={handleSend} className="p-2.5 bg-indigo-600 rounded-full hover:bg-indigo-700"><Send size={20} className="text-white"/></button>
            <button onPointerDown={e=>{e.preventDefault();startRecording();}} onPointerUp={e=>{e.preventDefault();stopRecording();}} className={`p-2.5 rounded-full ${isRecording?'bg-red-500 animate-pulse':'bg-slate-700 hover:bg-slate-600'}`} style={{touchAction:'none'}}>{isRecording?<Square size={20} className="text-white"/>:<Mic size={20} className="text-white"/>}</button>
          </div>
        </div>
      ) : (
        /* VIDEO PREVIEW with language selector */
        <div className="flex flex-col items-end gap-1 preview-container">
          {/* Language dropdown above video */}
          <select 
            value={language}
            onChange={(e) => { 
              const newLang = e.target.value; 
              setLanguage(newLang); 
              localStorage.setItem('bizdnaii_widget_lang', newLang); 
              setTimeout(() => playVoice('hello', newLang), 100);
              handleOpen(); 
            }}
            onBlur={() => handleOpen()}
            style={{ width: '160px' }} className=" bg-slate-800/90 text-white text-xs rounded-lg px-2 py-1.5 focus:outline-none cursor-pointer preview-select"
            style={{ boxShadow: '0 0 10px rgba(0, 212, 255, 0.6), 0 0 20px rgba(0, 212, 255, 0.3)', border: '1px solid rgba(0, 212, 255, 0.5)' }}
          >
            
            {Object.entries(LANG_LABELS).map(([code, label]) => (<option key={code} value={code}>{label}</option>))}
          </select>
          
          {/* Video preview */}
          <div className="cursor-pointer relative preview-video" style={{ width: '160px', height: '200px' }} onClick={handleOpen}>
            <video ref={previewVideoRef} className="hidden" muted playsInline />
            <canvas ref={previewCanvasRef} width="160" height="200" className="rounded-2xl shadow-2xl preview-canvas" style={{ background: '#1a1a1a' }} />
            <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full text-xs text-white font-medium whitespace-nowrap shadow-lg push-btn">
              ➜ {t.push}
            </div>
            <div className="absolute inset-0 rounded-2xl border-2 border-cyan-400 opacity-50 animate-pulse pointer-events-none"/>
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes ping{75%,100%{transform:scale(1.8);opacity:0}}
        @keyframes glow{0%,100%{box-shadow:0 0 5px #06b6d4,0 0 10px #06b6d4}50%{box-shadow:0 0 20px #a855f7,0 0 30px #a855f7}}
        .push-btn{animation:glow 3s ease-in-out infinite}
        select option{background-color:#1e293b;color:white}
      `}</style>
    </div>
  );
}
