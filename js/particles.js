import * as THREE from 'https://cdn.skypack.dev/three@0.132.2';

class ParticleSystem {
    constructor() {
        this.particleCount = 1000;
        this.particles = new THREE.Group();
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({
            canvas: document.querySelector('#bg'),
            alpha: true
        });

        this.init();
        this.animate();
    }

    init() {
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.camera.position.z = 30;

        // Create particles
        const particleGeometry = new THREE.SphereGeometry(0.05, 8, 8);
        const particleMaterial = new THREE.MeshBasicMaterial({
            color: 0xD4AF37,
            transparent: true,
            opacity: 0.6
        });

        for (let i = 0; i < this.particleCount; i++) {
            const particle = new THREE.Mesh(particleGeometry, particleMaterial);
            
            // Random position
            particle.position.x = (Math.random() - 0.5) * 100;
            particle.position.y = (Math.random() - 0.5) * 100;
            particle.position.z = (Math.random() - 0.5) * 100;
            
            // Random velocity
            particle.velocity = new THREE.Vector3(
                (Math.random() - 0.5) * 0.05,
                (Math.random() - 0.5) * 0.05,
                (Math.random() - 0.5) * 0.05
            );

            this.particles.add(particle);
        }

        this.scene.add(this.particles);

        // Add ambient light
        const ambientLight = new THREE.AmbientLight(0xD4AF37, 0.5);
        this.scene.add(ambientLight);

        // Handle window resize
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    animate() {
        requestAnimationFrame(this.animate.bind(this));

        // Update particle positions
        this.particles.children.forEach(particle => {
            particle.position.add(particle.velocity);

            // Reset position if particle goes too far
            if (Math.abs(particle.position.x) > 50) particle.position.x *= -0.9;
            if (Math.abs(particle.position.y) > 50) particle.position.y *= -0.9;
            if (Math.abs(particle.position.z) > 50) particle.position.z *= -0.9;
        });

        // Rotate entire particle system
        this.particles.rotation.x += 0.0003;
        this.particles.rotation.y += 0.0005;

        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize particle system when document is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ParticleSystem();
});
