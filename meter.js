const Meter = {
    getSVG: function() {
        return `
            <div class="meter-wrapper">
                <svg viewBox="180 20 540 660" class="meter-svg" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="casePlastic" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#ffffff"/>
                      <stop offset="5%" stop-color="#f7f7f7"/>
                      <stop offset="95%" stop-color="#e6e6e6"/>
                      <stop offset="100%" stop-color="#dcdcdc"/>
                    </linearGradient>

                    <linearGradient id="panelPlastic" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#f0f0f0"/>
                      <stop offset="100%" stop-color="#e0e0e0"/>
                    </linearGradient>

                    <linearGradient id="displayBg" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#fcfcfc"/>
                      <stop offset="100%" stop-color="#f0f0f0"/>
                    </linearGradient>

                    <linearGradient id="stripeBlue" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#3b82f6"/>
                      <stop offset="100%" stop-color="#60a5fa"/>
                    </linearGradient>

                    <linearGradient id="rollerWhite" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#e6e6e6"/>
                      <stop offset="20%" stop-color="#ffffff"/>
                      <stop offset="50%" stop-color="#ffffff"/>
                      <stop offset="80%" stop-color="#f0f0f0"/>
                      <stop offset="100%" stop-color="#e6e6e6"/>
                    </linearGradient>

                    <linearGradient id="rollerRed" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stop-color="#d32f2f"/>
                      <stop offset="20%" stop-color="#f44336"/>
                      <stop offset="50%" stop-color="#e53935"/>
                      <stop offset="80%" stop-color="#d32f2f"/>
                      <stop offset="100%" stop-color="#b71c1c"/>
                    </linearGradient>

                    <filter id="ledGlow">
                      <feGaussianBlur stdDeviation="4" result="blur1"/>
                      <feMerge>
                        <feMergeNode in="blur1"/>
                        <feMergeNode in="SourceGraphic"/>
                      </feMerge>
                    </filter>

                    <filter id="softShadow">
                      <feGaussianBlur stdDeviation="8"/>
                      <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.15 0"/>
                    </filter>
                     <filter id="innerShadow">
                       <feOffset dx="0" dy="2"/>
                       <feGaussianBlur stdDeviation="2" result="offset-blur"/>
                       <feComposite operator="out" in="SourceGraphic" in2="offset-blur" result="inverse"/>
                       <feFlood flood-color="black" flood-opacity="0.2" result="color"/>
                       <feComposite operator="in" in="color" in2="inverse" result="shadow"/>
                       <feComposite operator="over" in="shadow" in2="SourceGraphic"/>
                    </filter>

                    <g id="digitColumnBlack">
                      <text x="20" y="42" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">0</text>
                      <text x="20" y="92" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">1</text>
                      <text x="20" y="142" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">2</text>
                      <text x="20" y="192" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">3</text>
                      <text x="20" y="242" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">4</text>
                      <text x="20" y="292" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">5</text>
                      <text x="20" y="342" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">6</text>
                      <text x="20" y="392" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">7</text>
                      <text x="20" y="442" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">8</text>
                      <text x="20" y="492" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">9</text>
                      <text x="20" y="542" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#222" text-anchor="middle">0</text>
                    </g>

                    <g id="digitColumnWhite">
                       <text x="20" y="42" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">0</text>
                      <text x="20" y="92" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">1</text>
                      <text x="20" y="142" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">2</text>
                      <text x="20" y="192" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">3</text>
                      <text x="20" y="242" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">4</text>
                      <text x="20" y="292" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">5</text>
                      <text x="20" y="342" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">6</text>
                      <text x="20" y="392" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">7</text>
                      <text x="20" y="442" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">8</text>
                      <text x="20" y="492" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">9</text>
                      <text x="20" y="542" font-family="'Courier New', monospace" font-size="38" font-weight="bold" fill="#fff" text-anchor="middle">0</text>
                    </g>

                    <clipPath id="windowClip">
                      <rect x="0" y="0" width="280" height="60" rx="2"/>
                    </clipPath>
                  </defs>

                  <g transform="translate(210, 50)">
                    
                    <rect x="15" y="25" width="450" height="570" rx="15" fill="#000" filter="url(#softShadow)"/>

                    <rect x="0" y="0" width="480" height="600" rx="12" fill="url(#casePlastic)" stroke="#d1d1d6" stroke-width="1"/>

                    <rect x="10" y="10" width="460" height="150" rx="6" fill="url(#panelPlastic)" stroke="#e5e5ea"/>
                    <rect x="190" y="130" width="100" height="12" rx="6" fill="#d1d1d6" opacity="0.4"/>
                    <circle cx="240" cy="136" r="3" fill="#a0a0a0"/>

                    <rect x="10" y="440" width="460" height="150" rx="6" fill="url(#panelPlastic)" stroke="#e5e5ea"/>
                    <rect x="190" y="458" width="100" height="12" rx="6" fill="#d1d1d6" opacity="0.4"/>
                    <circle cx="240" cy="464" r="3" fill="#a0a0a0"/>

                    <g transform="translate(10, 165)">
                      <rect x="0" y="0" width="460" height="270" rx="4" fill="url(#displayBg)" stroke="#c7c7cc" stroke-width="1"/>

                      <circle cx="20" cy="20" r="5" fill="#e5e5ea" stroke="#c7c7cc"/><line x1="17" y1="17" x2="23" y2="23" stroke="#a0a0a0"/>
                      <circle cx="440" cy="20" r="5" fill="#e5e5ea" stroke="#c7c7cc"/><line x1="437" y1="17" x2="443" y2="23" stroke="#a0a0a0"/>
                      <circle cx="20" cy="250" r="5" fill="#e5e5ea" stroke="#c7c7cc"/><line x1="17" y1="247" x2="23" y2="253" stroke="#a0a0a0"/>
                      <circle cx="440" cy="250" r="5" fill="#e5e5ea" stroke="#c7c7cc"/><line x1="437" y1="247" x2="443" y2="253" stroke="#a0a0a0"/>

                      <rect x="120" y="25" width="310" height="20" rx="2" fill="url(#stripeBlue)"/>
                      
                      <text x="30" y="75" font-family="Arial, sans-serif" font-weight="bold" font-size="13" fill="#48484a">A = 3200 imp/kW·h</text>
                      <text x="210" y="75" font-family="Arial, sans-serif" font-weight="bold" font-size="13" fill="#48484a" text-anchor="middle">230V 5-60A 50 Hz</text>
                      <text x="430" y="75" font-family="Arial, sans-serif" font-size="12" fill="#666" text-anchor="end">R5 145 M6</text>

                      <rect x="100" y="110" width="340" height="70" rx="4" fill="#f0f0f0" stroke="#c7c7cc" stroke-width="1" filter="url(#innerShadow)"/>
                      
                      <g transform="translate(110, 115)" clip-path="url(#windowClip)">
                        <g transform="translate(0, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerWhite)"/>
                          <use href="#digitColumnBlack">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="5000s" repeatCount="indefinite"/>
                          </use>
                        </g>
                        <g transform="translate(45, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerWhite)"/>
                          <use href="#digitColumnBlack">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="500s" repeatCount="indefinite"/>
                          </use>
                        </g>
                        <g transform="translate(90, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerWhite)"/>
                          <use href="#digitColumnBlack">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="100s" repeatCount="indefinite"/>
                          </use>
                        </g>
                        <g transform="translate(135, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerWhite)"/>
                          <use href="#digitColumnBlack">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="25s" repeatCount="indefinite"/>
                          </use>
                        </g>
                        <g transform="translate(180, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerWhite)"/>
                          <use href="#digitColumnBlack">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="5s" repeatCount="indefinite"/>
                          </use>
                        </g>
                        <g transform="translate(225, 0)">
                          <rect width="40" height="60" rx="1" fill="url(#rollerRed)"/>
                          <use href="#digitColumnWhite">
                            <animateTransform attributeName="transform" type="translate" values="0 0; 0 -500" dur="1.0s" repeatCount="indefinite"/>
                          </use>
                        </g>
                      </g>

                      <rect x="333" y="113" width="44" height="64" rx="2" fill="none" stroke="#d32f2f" stroke-width="2" opacity="0.5"/>
                      
                      <text x="385" y="152" font-family="Arial, sans-serif" font-weight="bold" font-size="18" fill="#8e8e93">kW·h</text>

                      <path d="M 100 110 L 440 110 L 440 135 Q 270 155 100 135 Z" fill="#ffffff" opacity="0.2"/>

                      <g transform="translate(55, 145)">
                        <circle cx="0" cy="0" r="8" fill="#e5e5ea" stroke="#c7c7cc" stroke-width="1"/>
                        <circle cx="0" cy="0" r="5" fill="#ff3b30" filter="url(#ledGlow)" opacity="0">
                          <animate attributeName="opacity" values="0.2; 1; 0.2; 0.2" keyTimes="0; 0.3; 0.6; 1" dur="1.2s" repeatCount="indefinite"/>
                        </circle>
                      </g>

                      <g transform="translate(35, 120)" stroke="#8e8e93" stroke-width="2" fill="none">
                         <polygon points="10,0 12,4 16,4 13,7 14,11 10,9 6,11 7,7 4,4 8,4"/>
                      </g>

                      <g transform="translate(100, 200)">
                        <rect x="0" y="0" width="340" height="45" fill="#fff" opacity="0.4" rx="4" stroke="#e5e5ea"/>
                        
                        <g fill="#48484a" transform="translate(10, 8)">
                          <rect x="0" y="0" width="2" height="18"/> <rect x="4" y="0" width="1" height="18"/> <rect x="7" y="0" width="3" height="18"/> <rect x="12" y="0" width="1" height="18"/> <rect x="15" y="0" width="4" height="18"/> <rect x="21" y="0" width="2" height="18"/> <rect x="25" y="0" width="1" height="18"/> <rect x="28" y="0" width="3" height="18"/> <rect x="33" y="0" width="2" height="18"/> <rect x="37" y="0" width="4" height="18"/> <rect x="43" y="0" width="1" height="18"/> <rect x="46" y="0" width="3" height="18"/>
                          <text x="0" y="28" font-family="'Courier New', monospace" font-size="10" letter-spacing="0.5">№007791128325</text>
                        </g>
                        
                        <g transform="translate(180, 8)">
                            <text x="0" y="8" font-family="Arial, sans-serif" font-size="9" fill="#666">ГОСТ 31818.11-2012</text>
                            <text x="0" y="20" font-family="Arial, sans-serif" font-size="9" fill="#666">ГОСТ 31819.21-2012</text>
                            
                            <g transform="translate(110, -2)">
                                <text x="5" y="16" font-family="Arial, sans-serif" font-weight="bold" font-size="14" fill="#48484a">EAC</text>
                                <rect x="0" y="0" width="38" height="22" fill="none" stroke="#8e8e93" stroke-width="1" rx="2"/>
                            </g>
                        </g>
                      </g>
                      
                      <g transform="translate(30, 210)" stroke="#8e8e93" stroke-width="1.5" fill="none">
                        <polygon points="15,0 30,25 0,25"/>
                        <line x1="15" y1="8" x2="15" y2="18"/>
                        <circle cx="15" cy="22" r="1" fill="#8e8e93"/>
                      </g>
                    </g>
                  </g>
                </svg>
            </div>
        `;
    }
};
