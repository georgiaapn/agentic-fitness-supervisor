import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101820",
        slate: "#34404A",
        surface: "#F7F8F5",
        panel: "#FFFFFF",
        primary: "#167E76",
        recovery: "#C94C2E",
        nutrition: "#6D8F2F",
        trainer: "#315D9A",
        border: "#D8DED8"
      },
      fontFamily: {
        display: ["Sora", "Inter", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        data: ["IBM Plex Mono", "ui-monospace", "monospace"]
      },
      borderRadius: {
        control: "8px",
        briefing: "12px"
      }
    }
  },
  plugins: []
};

export default config;

