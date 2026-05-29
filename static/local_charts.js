(function () {
  function color(i) {
    return ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#a855f7", "#22d3ee"][i % 6];
  }

  function finite(v, fallback) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  }

  function pointValue(p, key, fallback) {
    if (p && typeof p === "object") return finite(p[key], fallback);
    return finite(p, fallback);
  }

  function range(values, fallbackMin, fallbackMax) {
    const nums = values.map(Number).filter(Number.isFinite);
    if (!nums.length) return [fallbackMin, fallbackMax];
    let min = Math.min(...nums);
    let max = Math.max(...nums);
    if (min === max) {
      min -= 1;
      max += 1;
    }
    return [min, max];
  }

  function svgEl(name, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }

  function resolveElement(target) {
    return typeof target === "string" ? document.getElementById(target) : target;
  }

  function renderSvgPlot(target, traces, layout) {
    const host = resolveElement(target);
    if (!host) return Promise.resolve();
    const width = Math.max(host.clientWidth || 480, 260);
    const height = Math.max(host.clientHeight || 280, 180);
    host.innerHTML = "";
    host.classList.add("plotly", "local-plot");

    const svg = svgEl("svg", { width: "100%", height: "100%", viewBox: `0 0 ${width} ${height}` });
    const margin = { left: 46, right: 18, top: 34, bottom: 38 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const allX = [];
    const allY = [];
    (traces || []).forEach((tr) => {
      if (tr.type === "scatterternary") return;
      (tr.x || []).forEach((v) => allX.push(v));
      (tr.y || []).forEach((v) => allY.push(v));
    });
    const xRange = layout && layout.xaxis && layout.xaxis.range ? layout.xaxis.range : range(allX, 0, 1);
    const yRange = layout && layout.yaxis && layout.yaxis.range ? layout.yaxis.range : range(allY, 0, 1);
    const sx = (x) => margin.left + ((finite(x, xRange[0]) - xRange[0]) / (xRange[1] - xRange[0] || 1)) * plotW;
    const sy = (y) => margin.top + plotH - ((finite(y, yRange[0]) - yRange[0]) / (yRange[1] - yRange[0] || 1)) * plotH;

    svg.appendChild(svgEl("rect", { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: "rgba(255,255,255,0.04)", stroke: "rgba(255,255,255,0.12)" }));
    for (let i = 0; i <= 4; i++) {
      const x = margin.left + (plotW * i) / 4;
      const y = margin.top + (plotH * i) / 4;
      svg.appendChild(svgEl("line", { x1: x, y1: margin.top, x2: x, y2: margin.top + plotH, stroke: "rgba(255,255,255,0.06)" }));
      svg.appendChild(svgEl("line", { x1: margin.left, y1: y, x2: margin.left + plotW, y2: y, stroke: "rgba(255,255,255,0.06)" }));
    }

    const ternary = (traces || []).some((tr) => tr.type === "scatterternary");
    if (ternary) {
      renderTernary(svg, traces, width, height);
    } else {
      (traces || []).forEach((tr, idx) => {
        const xs = tr.x || [];
        const ys = tr.y || [];
        const pts = xs.map((x, i) => [sx(x), sy(ys[i])]).filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
        if (!pts.length) return;
        const stroke = tr.line && tr.line.color ? tr.line.color : color(idx);
        if ((tr.mode || "lines").includes("lines") && pts.length > 1) {
          svg.appendChild(svgEl("polyline", { points: pts.map((p) => p.join(",")).join(" "), fill: "none", stroke, "stroke-width": tr.line && tr.line.width ? tr.line.width : 2 }));
        }
        if ((tr.mode || "").includes("markers")) {
          pts.forEach(([x, y]) => svg.appendChild(svgEl("circle", { cx: x, cy: y, r: 3.5, fill: stroke })));
        }
      });
    }

    const title = layout && layout.title && (layout.title.text || layout.title);
    if (title) {
      const text = svgEl("text", { x: margin.left, y: 20, fill: "#f8fafc", "font-size": "13", "font-weight": "700" });
      text.textContent = String(title);
      svg.appendChild(text);
    }
    host.appendChild(svg);
    host.__localPlot = { traces: traces || [], layout: layout || {} };
    return Promise.resolve();
  }

  function renderTernary(svg, traces, width, height) {
    const cx = width / 2;
    const top = 38;
    const side = Math.min(width - 70, height - 70);
    const h = side * 0.86;
    const a = [cx, top];
    const b = [cx - side / 2, top + h];
    const c = [cx + side / 2, top + h];
    svg.appendChild(svgEl("polygon", { points: [a, b, c].map((p) => p.join(",")).join(" "), fill: "rgba(255,255,255,0.03)", stroke: "rgba(255,255,255,0.2)" }));
    const map = (av, bv, cv) => {
      const sum = finite(av, 0) + finite(bv, 0) + finite(cv, 0) || 1;
      return [
        (a[0] * av + b[0] * bv + c[0] * cv) / sum,
        (a[1] * av + b[1] * bv + c[1] * cv) / sum,
      ];
    };
    (traces || []).forEach((tr, idx) => {
      if (tr.type !== "scatterternary") return;
      const pts = (tr.a || []).map((av, i) => map(av, (tr.b || [])[i], (tr.c || [])[i]));
      const stroke = tr.line && tr.line.color ? tr.line.color : color(idx);
      if ((tr.mode || "lines").includes("lines") && pts.length > 1) {
        svg.appendChild(svgEl("polyline", { points: pts.map((p) => p.join(",")).join(" "), fill: "none", stroke, "stroke-width": tr.line && tr.line.width ? tr.line.width : 2 }));
      }
      if ((tr.mode || "").includes("markers")) {
        pts.forEach(([x, y]) => svg.appendChild(svgEl("circle", { cx: x, cy: y, r: 4, fill: stroke })));
      }
    });
  }

  if (typeof window.Plotly === "undefined") {
    window.Plotly = {
      newPlot: renderSvgPlot,
      react: renderSvgPlot,
      addTraces(target, trace) {
        const host = resolveElement(target);
        const current = host && host.__localPlot ? host.__localPlot : { traces: [], layout: {} };
        const traces = current.traces.concat(Array.isArray(trace) ? trace : [trace]);
        return renderSvgPlot(target, traces, current.layout);
      },
      animate(target, frames, opts) {
        let idx = 0;
        const step = () => {
          if (!frames || idx >= frames.length) return;
          const host = resolveElement(target);
          const current = host && host.__localPlot ? host.__localPlot : { layout: {} };
          renderSvgPlot(target, frames[idx].data || [], current.layout);
          idx += 1;
          setTimeout(step, (opts && opts.frame && opts.frame.duration) || 120);
        };
        step();
      },
      Plots: { resize() {} },
      toImage() { return Promise.reject(new Error("Export image indisponible avec le rendu local.")); },
    };
  }

  if (typeof window.Chart === "undefined") {
    window.Chart = class LocalChart {
      static defaults = { color: "#94a3b8", font: { family: "Inter" } };
      constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config || {};
        this.draw();
      }
      destroy() {}
      draw() {
        const canvas = this.ctx.canvas;
        const rect = canvas.getBoundingClientRect();
        canvas.width = Math.max(rect.width || 480, 260);
        canvas.height = Math.max(rect.height || 280, 180);
        const ctx = this.ctx;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "rgba(255,255,255,0.04)";
        ctx.fillRect(42, 22, canvas.width - 58, canvas.height - 58);
        const datasets = (this.config.data && this.config.data.datasets) || [];
        const labels = (this.config.data && this.config.data.labels) || [];
        const allX = [];
        const allY = [];
        datasets.forEach((ds) => {
          (ds.data || []).forEach((p, i) => {
            allX.push(pointValue(p, "x", labels[i] !== undefined ? i : i));
            allY.push(pointValue(p, "y", p));
          });
        });
        const xr = range(allX, 0, Math.max(labels.length - 1, 1));
        const yr = range(allY, 0, 1);
        const sx = (x) => 42 + ((x - xr[0]) / (xr[1] - xr[0] || 1)) * (canvas.width - 58);
        const sy = (y) => 22 + (canvas.height - 58) - ((y - yr[0]) / (yr[1] - yr[0] || 1)) * (canvas.height - 58);
        datasets.forEach((ds, idx) => {
          const stroke = ds.borderColor || color(idx);
          ctx.strokeStyle = stroke;
          ctx.fillStyle = ds.backgroundColor || stroke;
          ctx.lineWidth = 2;
          ctx.beginPath();
          (ds.data || []).forEach((p, i) => {
            const x = sx(pointValue(p, "x", labels[i] !== undefined ? i : i));
            const y = sy(pointValue(p, "y", p));
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          if (ds.showLine !== false) ctx.stroke();
        });
      }
    };
  }
})();
