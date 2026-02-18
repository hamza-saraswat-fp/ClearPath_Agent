"use client";

import { motion } from "framer-motion";

interface ClearPathLogoProps {
  size?: number;
  className?: string;
}

export function ClearPathLogo({ size = 64, className = "" }: ClearPathLogoProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`relative ${className}`}
      style={{ width: size, height: size }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 200 200"
        width="100%"
        height="100%"
      >
        <g clipPath="url(#cp_clip)">
          <mask
            id="cp_mask"
            style={{ maskType: "alpha" }}
            width="200"
            height="200"
            x="0"
            y="0"
            maskUnits="userSpaceOnUse"
          >
            <path
              fill="#fff"
              fillRule="evenodd"
              d="M100 150c27.614 0 50-22.386 50-50s-22.386-50-50-50-50 22.386-50 50 22.386 50 50 50zm0 50c55.228 0 100-44.772 100-100S155.228 0 100 0 0 44.772 0 100s44.772 100 100 100z"
              clipRule="evenodd"
            />
          </mask>
          <g mask="url(#cp_mask)">
            <path fill="#fff" d="M200 0H0v200h200V0z" />
            <path fill="#0066FF" fillOpacity="0.33" d="M200 0H0v200h200V0z" />
            <g filter="url(#cp_blur)" className="animate-gradient">
              <path fill="#0066FF" d="M110 32H18v68h92V32z" />
              <path fill="#0044FF" d="M188-24H15v98h173v-98z" />
              <path fill="#0099FF" d="M175 70H5v156h170V70z" />
              <path fill="#00CCFF" d="M230 51H100v103h130V51z" />
            </g>
          </g>
        </g>
        <defs>
          <filter
            id="cp_blur"
            width="385"
            height="410"
            x="-75"
            y="-104"
            colorInterpolationFilters="sRGB"
            filterUnits="userSpaceOnUse"
          >
            <feFlood floodOpacity="0" result="BackgroundImageFix" />
            <feBlend in="SourceGraphic" in2="BackgroundImageFix" result="shape" />
            <feGaussianBlur result="blur" stdDeviation="40" />
          </filter>
          <clipPath id="cp_clip">
            <path fill="#fff" d="M0 0H200V200H0z" />
          </clipPath>
        </defs>
        <g style={{ mixBlendMode: "overlay" }} mask="url(#cp_mask)">
          <path
            fill="gray"
            stroke="transparent"
            d="M200 0H0v200h200V0z"
            filter="url(#cp_noise)"
          />
        </g>
        <defs>
          <filter
            id="cp_noise"
            width="100%"
            height="100%"
            x="0%"
            y="0%"
            filterUnits="objectBoundingBox"
          >
            <feTurbulence
              baseFrequency="0.6"
              numOctaves="5"
              result="out1"
              seed="4"
            />
            <feComposite in="out1" in2="SourceGraphic" operator="in" result="out2" />
            <feBlend in="SourceGraphic" in2="out2" mode="overlay" result="out3" />
          </filter>
        </defs>
      </svg>
    </motion.div>
  );
}
