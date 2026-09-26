export function speakerDetailColumnCount (availableWidth, cardWidth, gap = 18) {
	const card = Number(cardWidth)
	if (!Number.isFinite(card) || card <= 0) return 1
	const available = Number(availableWidth)
	if (!Number.isFinite(available) || available <= 0) return 1
	const spacing = Number(gap)
	const safeGap = Number.isFinite(spacing) && spacing >= 0 ? spacing : 0
	return Math.max(1, Math.floor((available + safeGap) / (card + safeGap)))
}
