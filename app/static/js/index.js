// Smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();

        document.querySelector(this.getAttribute('href'))
            .scrollIntoView({
                behavior: 'smooth'
            });
    });
});

// Navbar effect
window.addEventListener('scroll', () => {
    const nav = document.querySelector('nav');
    if (!nav) return;

    if (window.scrollY > 50) {
        nav.classList.add('scrolled');
    } else {
        nav.classList.remove('scrolled');
    }
});
// Reveal cards
const cards = document.querySelectorAll(
    '.feature-card, .step-card'
);

const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if(entry.isIntersecting){
            entry.target.classList.add('show');
        }
    });
});

cards.forEach(card => {
    observer.observe(card);
});
const counters = document.querySelectorAll('.counter');

let started = false;

const runCounters = () => {
    if (started) return;
    started = true;

    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        let count = 0;

        const update = () => {
            const increment = Math.ceil(target / 100);

            if (count < target) {
                count += increment;
                if (count > target) count = target;

                counter.textContent = count;
                requestAnimationFrame(update);
            }
        };

        update();
    });
};

window.addEventListener('scroll', () => {
    const stats = document.querySelector('.stats-bar');
    if (!stats) return;

    const rect = stats.getBoundingClientRect();

    if (rect.top < window.innerHeight - 100) {
        runCounters();
    }
});

function toggleFAQ() {
    const faq = document.getElementById("faq-section");
    const arrow = document.getElementById("arrow");

    faq.classList.toggle("faq-show");
    faq.classList.toggle("faq-hidden");

    // rotate arrow
    if (faq.classList.contains("faq-show")) {
        arrow.textContent = "▲";
    } else {
        arrow.textContent = "▼";
    }
}
