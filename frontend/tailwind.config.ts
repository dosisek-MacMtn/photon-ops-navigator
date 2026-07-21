import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111c",
        panel: "#0d1c29",
        cyan: "#2fc3e8",
        amber: "#f2a93b",
        alarm: "#f45b69",
        snow: "#e9f2f6"
      }
    }
  },
  plugins: []
};

export default config;
