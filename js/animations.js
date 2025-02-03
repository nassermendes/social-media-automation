import gsap from 'https://cdn.skypack.dev/gsap';

class Animations {
    constructor() {
        this.initializeAnimations();
        this.setupEventListeners();
    }

    initializeAnimations() {
        // Initial page load animation
        gsap.from('.header h1', {
            duration: 1.5,
            y: -100,
            opacity: 0,
            ease: 'power4.out'
        });

        gsap.from('.header p', {
            duration: 1.5,
            y: 50,
            opacity: 0,
            ease: 'power4.out',
            delay: 0.2
        });

        gsap.from('.upload-card', {
            duration: 1.5,
            scale: 0.8,
            opacity: 0,
            ease: 'power4.out',
            delay: 0.4
        });

        // Add floating animation to upload icon
        gsap.to('.upload-icon', {
            y: -10,
            duration: 1.5,
            repeat: -1,
            yoyo: true,
            ease: 'power1.inOut'
        });
    }

    setupEventListeners() {
        // Hover animations for platform cards
        document.querySelectorAll('.platform-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                gsap.to(card, {
                    scale: 1.02,
                    duration: 0.3,
                    ease: 'power2.out'
                });

                // Animate the progress bar
                const progressBar = card.querySelector('.progress-fill');
                if (progressBar) {
                    gsap.to(progressBar, {
                        scaleX: 1.1,
                        duration: 0.3,
                        ease: 'power2.out'
                    });
                }
            });

            card.addEventListener('mouseleave', () => {
                gsap.to(card, {
                    scale: 1,
                    duration: 0.3,
                    ease: 'power2.out'
                });

                // Reset progress bar animation
                const progressBar = card.querySelector('.progress-fill');
                if (progressBar) {
                    gsap.to(progressBar, {
                        scaleX: 1,
                        duration: 0.3,
                        ease: 'power2.out'
                    });
                }
            });
        });

        // Upload button hover animation
        const uploadButton = document.getElementById('uploadButton');
        if (uploadButton) {
            uploadButton.addEventListener('mouseenter', () => {
                gsap.to(uploadButton, {
                    scale: 1.05,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });

            uploadButton.addEventListener('mouseleave', () => {
                gsap.to(uploadButton, {
                    scale: 1,
                    duration: 0.3,
                    ease: 'power2.out'
                });
            });
        }
    }

    // Animation for when a new platform card appears
    animatePlatformCard(card) {
        gsap.from(card, {
            duration: 0.8,
            scale: 0.5,
            opacity: 0,
            ease: 'back.out(1.7)',
            clearProps: 'all'
        });
    }

    // Success animation
    animateSuccess(element) {
        gsap.to(element, {
            keyframes: [
                { scale: 1.1, duration: 0.2 },
                { scale: 1, duration: 0.2 },
                { scale: 1.05, duration: 0.2 },
                { scale: 1, duration: 0.2 }
            ],
            ease: 'power2.out'
        });
    }

    // Error animation
    animateError(element) {
        gsap.to(element, {
            keyframes: [
                { x: -10, duration: 0.1 },
                { x: 10, duration: 0.1 },
                { x: -5, duration: 0.1 },
                { x: 5, duration: 0.1 },
                { x: 0, duration: 0.1 }
            ],
            ease: 'power2.out'
        });
    }
}

// Initialize animations when document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.animations = new Animations();
});
