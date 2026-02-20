const Flashlight = {
    getSVG: function() {
        return `
            <div id="flashlight-wrapper" class="flashlight-wrapper" onclick="Flashlight.toggle(this)">
                <svg viewBox="-20 -150 450 300" class="fl-svg" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="bodyMetal" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#5a5e65"/>
                      <stop offset="10%" stop-color="#2a2d32"/>
                      <stop offset="45%" stop-color="#181a1d"/>
                      <stop offset="85%" stop-color="#2a2d32"/>
                      <stop offset="100%" stop-color="#4a4d54"/>
                    </linearGradient>
                    <linearGradient id="headMetal" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#6b7078"/>
                      <stop offset="15%" stop-color="#32363d"/>
                      <stop offset="50%" stop-color="#1c1e22"/>
                      <stop offset="85%" stop-color="#32363d"/>
                      <stop offset="100%" stop-color="#555960"/>
                    </linearGradient>
                    <linearGradient id="accentRing" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#999999"/> <stop offset="50%" stop-color="#555555"/>
                      <stop offset="100%" stop-color="#aaaaaa"/>
                    </linearGradient>
                    <linearGradient id="buttonRubber" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#ff3b30"/>
                      <stop offset="100%" stop-color="#8a0000"/>
                    </linearGradient>
                    <radialGradient id="lensOff" cx="50%" cy="50%" r="50%">
                      <stop offset="50%" stop-color="#000000"/>
                      <stop offset="100%" stop-color="#2a2d35"/>
                    </radialGradient>
                    <radialGradient id="lensOn" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/> <stop offset="40%" stop-color="#f0f8ff"/> <stop offset="80%" stop-color="#add8e6"/>
                      <stop offset="100%" stop-color="#00bfff"/> 
                    </radialGradient>
                    <linearGradient id="beamCore" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
                      <stop offset="30%" stop-color="#e0f7fa" stop-opacity="0.5"/>
                      <stop offset="100%" stop-color="#0ea5e9" stop-opacity="0"/>
                    </linearGradient>
                    <linearGradient id="beamAmbient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.3"/>
                      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
                    </linearGradient>
                    <filter id="cleanGlow" x="-150%" y="-150%" width="400%" height="400%" color-interpolation-filters="sRGB">
                      <feGaussianBlur stdDeviation="8" result="blur1"/>
                       <feMerge>
                        <feMergeNode in="blur1"/>
                        <feMergeNode in="blur1"/>
                        <feMergeNode in="SourceGraphic"/>
                      </feMerge>
                    </filter>
                    <filter id="beamBlur" x="-20%" y="-50%" width="140%" height="200%" color-interpolation-filters="sRGB">
                      <feGaussianBlur stdDeviation="25"/>
                    </filter>
                  </defs>

                  <g transform="translate(30, 0)"> 
                    
                    <g class="fl-hint-icon">
                        <text x="175" y="-65" font-size="34" text-anchor="middle">👇</text>
                    </g>

                    <g class="fl-sway">
                      <g class="fl-beam" style="mix-blend-mode: screen; pointer-events: none;">
                        <polygon points="270,-50 950,-280 950,280 270,50" fill="url(#beamAmbient)" filter="url(#beamBlur)"/>
                        <polygon points="270,-22 900,-90 900,90 270,22" fill="url(#beamCore)" filter="url(#beamBlur)"/>
                      </g>

                      <rect x="0" y="-35" width="220" height="70" rx="6" fill="url(#bodyMetal)"/>

                      <g stroke="#111" stroke-width="1.5" opacity="0.4">
                        <line x1="30" y1="-35" x2="30" y2="35"/>
                        <line x1="60" y1="-35" x2="60" y2="35"/>
                        <line x1="90" y1="-35" x2="90" y2="35"/>
                        <line x1="120" y1="-35" x2="120" y2="35"/>
                        <line x1="150" y1="-35" x2="150" y2="35"/>
                        <line x1="180" y1="-35" x2="180" y2="35"/>
                      </g>

                      <g transform="translate(110, 0)"> 
                          <path d="M105,-35 L145,-58 L162,-58 L162,58 L145,58 L105,35 Z" fill="url(#headMetal)"/>
                          <rect x="120" y="-48" width="3" height="96" rx="1" fill="#111" opacity="0.5"/>
                          <rect x="130" y="-53" width="3" height="106" rx="1" fill="#111" opacity="0.5"/>
                          <rect x="140" y="-56" width="3" height="112" rx="1" fill="#111" opacity="0.5"/>
                          <rect x="157" y="-60" width="5" height="120" rx="2" fill="url(#accentRing)"/>
                      </g>

                      <g transform="translate(180, -35)">
                        <rect x="-14" y="-2" width="28" height="5" rx="2" fill="#0a0a0c"/>
                        <rect x="-12" y="-8" width="24" height="8" rx="3" fill="url(#buttonRubber)" class="fl-btn"/>
                      </g>

                      <g transform="translate(110, 0)">
                          <ellipse cx="164" cy="0" rx="5" ry="57" fill="url(#lensOff)"/>
                          <ellipse cx="164" cy="0" rx="5" ry="57" fill="url(#lensOn)" filter="url(#cleanGlow)" class="fl-lens"/>
                          <path d="M164,-58 Q172,0 164,58 Q160,0 164,-58 Z" fill="#fff" opacity="0.1"/>
                      </g>
                    </g> 
                  </g>
                </svg>
            </div>`;
    },

    toggle: function(wrapper) {
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
        } else if (navigator.vibrate) {
            navigator.vibrate(40);
        }

        wrapper.classList.toggle('is-on');
        
        const sway = wrapper.querySelector('.fl-sway');
        if (sway) {
            sway.classList.remove('shake-anim');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    sway.classList.add('shake-anim');
                });
            });
        }
    }
};
