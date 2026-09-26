/**
 * Column counts for the public speakers photo grid.
 * Run: node --test src/speakerColumns.test.js
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { speakerDetailColumnCount } from './speakerColumns.js'

test('speaker detail columns never overflow the measured width', () => {
	assert.equal(speakerDetailColumnCount(0, 360), 1)
	assert.equal(speakerDetailColumnCount(359, 360), 1)
	assert.equal(speakerDetailColumnCount(360, 360), 1)
	assert.equal(speakerDetailColumnCount(737, 360), 1)
	assert.equal(speakerDetailColumnCount(738, 360), 2)
	assert.equal(speakerDetailColumnCount(1115, 360), 2)
	assert.equal(speakerDetailColumnCount(1116, 360), 3)
	assert.equal(speakerDetailColumnCount(1920, 360), 5)
})

test('speaker detail columns reject invalid measurements', () => {
	assert.equal(speakerDetailColumnCount(undefined, 360), 1)
	assert.equal(speakerDetailColumnCount(1200, 0), 1)
	assert.equal(speakerDetailColumnCount(1200, Number.NaN), 1)
})
