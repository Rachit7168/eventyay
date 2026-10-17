function gettext(msgid) {
    if (typeof django !== 'undefined' && django.gettext) {
        return django.gettext(msgid);
    }
    return msgid;
}

function emptyRecipient() {
    return { email: '', number: '', name: '', tag: '' };
}

function delimiterOutsideQuotes(line) {
    let quoted = false;
    let sawComma = false;
    let sawSemicolon = false;
    for (let index = 0; index < line.length; index += 1) {
        const char = line[index];
        if (quoted) {
            if (char === '"') {
                if (line[index + 1] === '"') {
                    index += 1;
                } else {
                    quoted = false;
                }
            }
        } else if (char === '"') {
            quoted = true;
        } else if (char === ',') {
            sawComma = true;
        } else if (char === ';') {
            sawSemicolon = true;
        }
    }
    if (sawSemicolon && !sawComma) {
        return ';';
    }
    if (sawComma) {
        return ',';
    }
    return '';
}

function splitCsvLine(line, delimiter) {
    const cells = [];
    let current = '';
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
        const char = line[index];
        if (quoted) {
            if (char === '"') {
                if (line[index + 1] === '"') {
                    current += '"';
                    index += 1;
                } else {
                    quoted = false;
                }
            } else {
                current += char;
            }
        } else if (char === '"') {
            quoted = true;
        } else if (char === delimiter) {
            cells.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    cells.push(current.trim());
    return cells;
}

function csvCell(value) {
    const text = String(value ?? '');
    if (/[",\n;]/.test(text)) {
        return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
}

function splitCsvRecords(raw) {
    const text = String(raw || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const records = [];
    let current = '';
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
        const char = text[index];
        if (char === '"') {
            current += char;
            if (quoted && text[index + 1] === '"') {
                current += text[index + 1];
                index += 1;
            } else {
                quoted = !quoted;
            }
        } else if (char === '\n' && !quoted) {
            if (current.trim()) {
                records.push(current.trim());
            }
            current = '';
        } else {
            current += char;
        }
    }
    if (current.trim()) {
        records.push(current.trim());
    }
    return records;
}

export function parseRecipients(raw) {
    const lines = splitCsvRecords(raw);
    if (!lines.length) {
        return [emptyRecipient()];
    }
    const delimiter = delimiterOutsideQuotes(lines[0]);
    if (!delimiter) {
        return lines.map((email) => ({ email, number: '', name: '', tag: '' }));
    }
    const first = splitCsvLine(lines[0], delimiter).map((cell) => cell.toLowerCase());
    const start = first.includes('email') ? 1 : 0;
    const header = start === 1 ? first : ['email', 'number', 'name', 'tag'];
    return lines.slice(start).map((line) => {
        const cells = splitCsvLine(line, delimiter);
        const record = emptyRecipient();
        header.forEach((column, index) => {
            if (column in record) {
                record[column] = cells[index] || '';
            }
        });
        return record;
    });
}

export function serializeRecipients(rows) {
    const filled = rows.filter((row) => row.email.trim() || row.number.trim() || row.name.trim() || row.tag.trim());
    if (!filled.length) {
        return '';
    }
    const hasDetails = filled.some((row) => row.name.trim() || row.tag.trim());
    const simple = filled.every((row) => !row.number.trim() || row.number.trim() === '1');
    if (!hasDetails && simple) {
        return filled.map((row) => row.email.trim()).join('\n');
    }
    if (!hasDetails) {
        const body = filled.map((row) => [row.email.trim(), row.number.trim() || '1'].map(csvCell).join(','));
        return ['email,number', ...body].join('\n');
    }
    const body = filled.map((row) =>
        [row.email.trim(), row.number.trim() || '1', row.name.trim(), row.tag.trim()].map(csvCell).join(','),
    );
    return ['email,number,name,tag', ...body].join('\n');
}

function createField(label, value, options) {
    const input = document.createElement('input');
    input.className = 'form-control input-sm';
    input.type = options.type || 'text';
    input.value = value;
    input.placeholder = label;
    input.setAttribute('aria-label', label);
    if (options.inputMode) {
        input.inputMode = options.inputMode;
    }
    return input;
}

function mountRecipients(textarea) {
    if (textarea.dataset.voucherRecipientsMounted) {
        return;
    }
    textarea.dataset.voucherRecipientsMounted = 'true';
    textarea.classList.add('voucher-recipients-source');

    const panel = document.createElement('div');
    panel.className = 'voucher-recipients';
    const heading = document.createElement('div');
    heading.className = 'voucher-recipients-columns';
    [gettext('Email'), gettext('Count'), ''].forEach((label) => {
        const cell = document.createElement('span');
        cell.textContent = label;
        heading.append(cell);
    });
    const list = document.createElement('div');
    list.className = 'voucher-recipients-list';
    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'btn btn-default btn-sm voucher-recipients-add';
    addButton.textContent = gettext('Add recipient');
    panel.append(heading, list, addButton);
    textarea.insertAdjacentElement('afterend', panel);

    let rows = parseRecipients(textarea.value);

    const write = () => {
        textarea.value = serializeRecipients(rows);
    };

    const render = () => {
        list.replaceChildren();
        rows.forEach((row, index) => {
            const line = document.createElement('div');
            line.className = 'voucher-recipient-row';
            const email = createField(gettext('Email address'), row.email, { type: 'email' });
            const number = createField(gettext('Count'), row.number, { type: 'text', inputMode: 'numeric' });
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'btn btn-link btn-sm voucher-recipient-remove';
            remove.setAttribute('aria-label', gettext('Remove recipient'));
            remove.textContent = '×';

            const bind = (input, key) => {
                input.addEventListener('input', () => {
                    rows[index][key] = input.value;
                    write();
                });
            };
            bind(email, 'email');
            bind(number, 'number');
            email.addEventListener('paste', (event) => {
                const text = event.clipboardData?.getData('text') || '';
                if (!text.includes('\n') && !text.includes(',')) {
                    return;
                }
                event.preventDefault();
                const pasted = parseRecipients(text).filter((item) => item.email.trim());
                if (!pasted.length) {
                    return;
                }
                rows.splice(index, 1, ...pasted);
                write();
                render();
            });
            remove.addEventListener('click', () => {
                if (rows.length === 1) {
                    rows = [emptyRecipient()];
                } else {
                    rows.splice(index, 1);
                }
                write();
                render();
            });
            line.append(email, number, remove);
            list.append(line);
        });
    };

    addButton.addEventListener('click', () => {
        rows.push(emptyRecipient());
        render();
        const inputs = list.querySelectorAll('input[type="email"]');
        inputs[inputs.length - 1]?.focus();
    });

    const form = textarea.closest('form');
    form?.addEventListener('submit', write);
    render();
    write();
}

export function initVoucherRecipients(root) {
    root.querySelectorAll('textarea[data-voucher-recipients]').forEach((textarea) => {
        mountRecipients(textarea);
    });
}
