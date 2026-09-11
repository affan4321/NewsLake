"use client";

import { useEffect, useRef, useState } from "react";

/*
 * A drag-to-rotate Earth made of dots, standing in for "news arrives from everywhere."
 * Deliberately Canvas 2D, not WebGL/three.js: a few hundred points projected with basic
 * perspective math is trivial for a 2D context, and it keeps the bundle free of a 600KB+
 * 3D dependency for something this simple.
 *
 * Rendering pipeline, every frame:
 *   1. rotate each point's fixed unit-sphere coordinate by the current drag/inertia angle
 *   2. project to screen space with a cheap perspective divide
 *   3. sort back-to-front (painter's algorithm) so the far hemisphere doesn't overdraw the near one
 *   4. draw, fading/shrinking points by depth
 */

type Point = { x: number; y: number; z: number };
type Ping = { point: Point; start: number };

const CONTINENTS: { lat: number; lon: number; radiusDeg: number }[] = [
  { lat: 45, lon: -100, radiusDeg: 26 }, // North America
  { lat: -15, lon: -60, radiusDeg: 22 }, // South America
  { lat: 52, lon: 12, radiusDeg: 13 }, // Europe
  { lat: 5, lon: 20, radiusDeg: 27 }, // Africa
  { lat: 48, lon: 90, radiusDeg: 38 }, // Asia
  { lat: -25, lon: 135, radiusDeg: 13 }, // Australia
];

function toUnitVector(latDeg: number, lonDeg: number): Point {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  return {
    x: Math.cos(lat) * Math.cos(lon),
    y: Math.sin(lat),
    z: Math.cos(lat) * Math.sin(lon),
  };
}

function buildLandPoints(count: number): Point[] {
  const continentVectors = CONTINENTS.map((c) => ({
    v: toUnitVector(c.lat, c.lon),
    cosThreshold: Math.cos((c.radiusDeg * Math.PI) / 180),
  }));

  const points: Point[] = [];
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const radiusAtY = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = goldenAngle * i;
    const p: Point = { x: Math.cos(theta) * radiusAtY, y, z: Math.sin(theta) * radiusAtY };

    const isLand = continentVectors.some(
      ({ v, cosThreshold }) => p.x * v.x + p.y * v.y + p.z * v.z > cosThreshold,
    );
    if (isLand) points.push(p);
  }
  return points;
}

export default function Globe() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const parent = canvas?.parentElement;
    if (!canvas || !parent) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isSmall = window.matchMedia("(max-width: 640px)").matches;
    const points = buildLandPoints(isSmall ? 2200 : 4200);

    let width = 0;
    let height = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      if (!canvas || !parent) return;
      width = parent.clientWidth;
      height = parent.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(parent);

    // Rotation state. rotY = spin around vertical axis, rotX = tilt.
    let rotY = 0.4;
    let rotX = -0.25;
    let velY = 0.0006;
    let velX = 0;
    let isDragging = false;
    let lastX = 0;
    let lastY = 0;
    let lastT = 0;

    const pings: Ping[] = [];
    let nextPingAt = performance.now() + 800;

    function onPointerDown(e: PointerEvent) {
      isDragging = true;
      setDragging(true);
      lastX = e.clientX;
      lastY = e.clientY;
      lastT = performance.now();
      canvas!.setPointerCapture(e.pointerId);
    }
    function onPointerMove(e: PointerEvent) {
      if (!isDragging) return;
      const now = performance.now();
      const dt = Math.max(now - lastT, 1);
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      rotY += dx * 0.006;
      rotX = Math.max(-1.1, Math.min(1.1, rotX - dy * 0.006));
      velY = (dx * 0.006) / (dt / 16.7);
      velX = (-dy * 0.006) / (dt / 16.7);
      lastX = e.clientX;
      lastY = e.clientY;
      lastT = now;
    }
    function onPointerUp(e: PointerEvent) {
      isDragging = false;
      setDragging(false);
      canvas!.releasePointerCapture(e.pointerId);
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);

    let raf = 0;
    let lastFrame = performance.now();

    function frame(now: number) {
      raf = requestAnimationFrame(frame);
      const dt = now - lastFrame;
      lastFrame = now;

      if (!isDragging) {
        if (!reducedMotion) {
          // Idle auto-spin: velocity decays toward a slow constant drift, not to zero.
          rotY += velY * (dt / 16.7);
          rotX += velX * (dt / 16.7);
          velY += (0.0006 - velY) * 0.02;
          velX *= 0.92;
        }
      }

      if (!reducedMotion && now >= nextPingAt && points.length > 0) {
        const point = points[Math.floor(Math.random() * points.length)];
        pings.push({ point, start: now });
        nextPingAt = now + 700 + Math.random() * 900;
      }

      const cx = width / 2;
      // On mobile, text and globe can't sit side by side the way they do on desktop —
      // push the globe lower and smaller so it clears the paragraph/CTA text instead of
      // sitting directly behind it.
      const cy = height * (isSmall ? 0.76 : 0.58);
      const radius = Math.min(width, height) * (isSmall ? 0.3 : 0.42);
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const focal = radius * 3;

      ctx!.clearRect(0, 0, width, height);

      const projected = points.map((p) => {
        const x1 = p.x * cosY + p.z * sinY;
        const z1 = -p.x * sinY + p.z * cosY;
        const y2 = p.y * cosX - z1 * sinX;
        const z2 = p.y * sinX + z1 * cosX;
        const perspective = focal / (focal + z2 * radius);
        return {
          sx: cx + x1 * radius * perspective,
          sy: cy - y2 * radius * perspective,
          z: z2,
        };
      });
      projected.sort((a, b) => a.z - b.z);

      for (const p of projected) {
        const depth = (p.z + 1) / 2; // 0 = far, 1 = near
        const alpha = 0.12 + depth * 0.75;
        const size = (1 + depth * 1.8) * dpr * 0.5;
        ctx!.fillStyle = `rgba(154, 174, 196, ${alpha})`;
        ctx!.beginPath();
        ctx!.arc(p.sx, p.sy, size, 0, Math.PI * 2);
        ctx!.fill();
      }

      // Faint sphere-edge rim so the globe reads as a solid body, not a dot cloud.
      ctx!.strokeStyle = "rgba(56, 189, 248, 0.12)";
      ctx!.lineWidth = 1;
      ctx!.beginPath();
      ctx!.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx!.stroke();

      for (let i = pings.length - 1; i >= 0; i--) {
        const ping = pings[i];
        const age = now - ping.start;
        const life = 1300;
        if (age > life) {
          pings.splice(i, 1);
          continue;
        }
        const x1 = ping.point.x * cosY + ping.point.z * sinY;
        const z1 = -ping.point.x * sinY + ping.point.z * cosY;
        const y2 = ping.point.y * cosX - z1 * sinX;
        const z2 = ping.point.y * sinX + z1 * cosX;
        if (z2 < -0.15) continue; // don't draw pings on the far side
        const perspective = focal / (focal + z2 * radius);
        const sx = cx + x1 * radius * perspective;
        const sy = cy - y2 * radius * perspective;
        const t = age / life;
        const ringRadius = 3 + t * 16;
        const alpha = (1 - t) * 0.7;

        ctx!.strokeStyle = `rgba(224, 178, 62, ${alpha})`;
        ctx!.lineWidth = 1.5;
        ctx!.beginPath();
        ctx!.arc(sx, sy, ringRadius, 0, Math.PI * 2);
        ctx!.stroke();

        ctx!.fillStyle = `rgba(56, 189, 248, ${Math.min(1, (1 - t) * 1.4)})`;
        ctx!.beginPath();
        ctx!.arc(sx, sy, 2 * dpr * 0.5, 0, Math.PI * 2);
        ctx!.fill();
      }
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={`h-full w-full touch-none select-none ${dragging ? "cursor-grabbing" : "cursor-grab"}`}
    />
  );
}
