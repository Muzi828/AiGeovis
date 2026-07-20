/**
 * 从边列表提取共现权重区间（忽略无效/非正权重）。
 */
export function edgeWeightRange(edges) {
  let minW = Infinity
  let maxW = -Infinity
  for (const edge of edges || []) {
    const w = Number(edge?.weight)
    if (!Number.isFinite(w) || w <= 0) continue
    if (w < minW) minW = w
    if (w > maxW) maxW = w
  }
  if (!Number.isFinite(minW)) return { minW: 1, maxW: 1 }
  return { minW, maxW }
}

/**
 * 将边权重映射为基准线宽。
 * 相对当前边集 min–max 归一化后再做幂次拉伸，使权重集中在 1–4 时仍有明显台阶。
 */
export function edgeWeightToBaseWidth(weight, minWeight, maxWeight, opts = {}) {
  const minPx = Number.isFinite(opts.minPx) ? opts.minPx : 0.75
  const maxPx = Number.isFinite(opts.maxPx) ? opts.maxPx : 3.8
  const power = Number.isFinite(opts.power) ? opts.power : 0.55
  const w = Math.max(1, Number(weight) || 1)
  const lo = Math.max(1, Number(minWeight) || 1)
  const hi = Math.max(lo, Number(maxWeight) || lo)
  if (hi === lo) return (minPx + maxPx) / 2
  const t = (w - lo) / (hi - lo)
  const curved = Math.pow(Math.max(0, Math.min(1, t)), power)
  return minPx + curved * (maxPx - minPx)
}
