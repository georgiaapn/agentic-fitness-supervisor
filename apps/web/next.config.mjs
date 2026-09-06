/** @type {import('next').NextConfig} */
const staticExport = process.env.NEXT_OUTPUT_MODE === "export";

const nextConfig = staticExport
  ? {
      output: "export",
      images: {
        unoptimized: true
      }
    }
  : {
      distDir: "next-build",
      output: "standalone"
    };

export default nextConfig;
