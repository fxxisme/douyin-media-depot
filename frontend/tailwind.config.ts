import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#202420",
        paper: "#F7F6F1",
        line: "#DAD7CD",
        moss: "#68765D",
        lake: "#426B78",
        ember: "#B85C38",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(32, 36, 32, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
