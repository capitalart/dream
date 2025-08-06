// THIS IS A TEST MIGRATION TEMPLATE. Safe to delete after production migration.
        document.addEventListener('DOMContentLoaded', () => {
            const menuToggle = document.getElementById('menu-toggle');
            const menuClose = document.getElementById('menu-close');
            const overlayMenu = document.getElementById('overlay-menu');
            const themeToggle = document.getElementById('theme-toggle');
            const rootEl = document.documentElement;

            // --- Menu Logic ---
            if (menuToggle && menuClose && overlayMenu) {
                menuToggle.addEventListener('click', () => {
                    overlayMenu.classList.add('is-active');
                    body.style.overflow = 'hidden';
                });

                menuClose.addEventListener('click', () => {
                    overlayMenu.classList.remove('is-active');
                    body.style.overflow = '';
                });
            }

            // --- Theme Logic ---
            const applyTheme = (theme) => {
                rootEl.classList.remove('theme-light', 'theme-dark');
                rootEl.classList.add('theme-' + theme);
                localStorage.setItem('theme', theme);
            };

            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const initial = savedTheme || (prefersDark ? 'dark' : 'light');
            applyTheme(initial);

            if (themeToggle) {
                themeToggle.addEventListener('click', () => {
                    const next = rootEl.classList.contains('theme-dark') ? 'light' : 'dark';
                    applyTheme(next);
                });
            }
            
            // --- Gemini Modal Logic ---
            const modal = document.getElementById('gemini-modal');
            const modalTitle = document.getElementById('gemini-modal-title');
            const modalBody = document.getElementById('gemini-modal-body');
            const closeBtn = document.querySelector('.gemini-modal-close');
            const copyBtn = document.getElementById('gemini-copy-btn');

            const defaultPrompts = {
                'generate-description': `Act as an expert art critic. Write an evocative and compelling gallery description for a piece of art titled "{ART_TITLE}". Focus on the potential materials, the mood it evokes, and the ideal setting for it. Make it about 150 words.`,
                'create-social-post': `Generate a short, engaging Instagram post to promote a piece of art titled "{ART_TITLE}". Include a catchy opening line, a brief description, and 3-5 relevant hashtags.`
            };

            closeBtn.onclick = () => {
                modal.style.display = "none";
            }
            window.onclick = (event) => {
                if (event.target == modal) {
                    modal.style.display = "none";
                }
            }

            document.querySelectorAll('.btn-gemini').forEach(button => {
                button.addEventListener('click', async (e) => {
                    const action = e.target.dataset.action;
                    const artPiece = e.target.closest('.art-piece');
                    const artTitle = artPiece.querySelector('h2').textContent;
                    
                    let promptTemplate = '';
                    let title = '';

                    if (action === 'generate-description') {
                        title = '✨ AI Art Description';
                        promptTemplate = localStorage.getItem('geminiDescriptionPrompt') || defaultPrompts[action];
                    } else if (action === 'create-social-post') {
                        title = '✨ AI Social Media Post';
                        promptTemplate = defaultPrompts[action]; // Using default for this one
                    }

                    const prompt = promptTemplate.replace('{ART_TITLE}', artTitle);

                    modalTitle.textContent = title;
                    modalBody.innerHTML = '<div class="loader"></div>';
                    modal.style.display = 'flex';

                    try {
                        let chatHistory = [{ role: "user", parts: [{ text: prompt }] }];
                        const payload = { contents: chatHistory };
                        const apiKey = ""; 
                        const apiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + apiKey;
                        
                        const response = await fetch(apiUrl, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        
                        if (!response.ok) {
                             throw new Error("API error: " + response.status + " " + response.statusText);
                        }

                        const result = await response.json();
                        
                        if (result.candidates && result.candidates.length > 0 &&
                            result.candidates[0].content && result.candidates[0].content.parts &&
                            result.candidates[0].content.parts.length > 0) {
                            const text = result.candidates[0].content.parts[0].text;
                            modalBody.innerHTML = '<textarea id="gemini-result">' + text + '</textarea>';
                        } else {
                            throw new Error("Invalid response structure from API.");
                        }

                    } catch (error) {
                        console.error("Gemini API call failed:", error);
                        modalBody.innerHTML = '<p>Sorry, something went wrong. Please try again. (' + error.message + ')</p>';
                    }
                });
            });
            
            copyBtn.addEventListener('click', () => {
                const resultTextarea = document.getElementById('gemini-result');
                if (resultTextarea) {
                    resultTextarea.select();
                    document.execCommand('copy');
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
                }
            });

        });
