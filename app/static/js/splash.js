document.addEventListener("DOMContentLoaded", () => {

    // Slight glow effect when hovering the logo

    const logo = document.querySelector(".logo");

    logo.addEventListener("mouseenter", () => {

        logo.style.transform = "translateY(-10px) scale(1.05)";

    });

    logo.addEventListener("mouseleave", () => {

        logo.style.transform = "";

    });

});