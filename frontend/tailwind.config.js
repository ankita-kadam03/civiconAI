/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cream: "#FBF7F2",
        foam: "#F4FAF7",
        navy: "#1B2545",
        ink: "#24324F",
        teal: "#2A9D8F",
        mint: "#D4F3EA",
        peach: "#F6C9A8",
        sun: "#F4D35E",
        lavender: "#E8E4FF",
        sky: "#D7EEFF",
        coral: "#FFB4A2",
      },
      fontFamily: {
        display: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Plus Jakarta Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 18px 50px -24px rgba(27, 37, 69, 0.28)",
        soft: "0 10px 28px -18px rgba(27, 37, 69, 0.22)",
      },
      borderRadius: {
        xl2: "1.5rem",
      },
    },
  },
  plugins: [],
};
