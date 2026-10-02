// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Tables: rows, columns, cells, free cells, themes and chips packed into a table.
// Code-behind for VkbRigEditor.qml (imported without .pragma library): it
// uses the editor's ids, properties and functions directly, and each
// function here has a forwarder of the same name in the editor.

function emptyTableRow(cols) {
    var row = { cells: [] }
    var i
    var count = Math.max(1, cols || 2)
    for (i = 0; i < count; i++)
        row.cells.push({ text: "" })
    return row
}

function ensureTable(n) {
    if (!isTable(n))
        return
    var cols = (n.cols > 0) ? n.cols : 2
    n.cols = cols
    if (!n.theme || !String(n.theme).length)
        n.theme = "gremlin"
    if (n.idCol === undefined || n.idCol === null)
        n.idCol = false
    if (!n.fontSize)
        n.fontSize = 10
    if (!n.extras)
        n.extras = []
    if (!n.rows || !n.rows.length)
        n.rows = [emptyTableRow(cols)]
    var r
    for (r = 0; r < n.rows.length; r++) {
        if (!n.rows[r])
            n.rows[r] = emptyTableRow(cols)
        if (!n.rows[r].cells)
            n.rows[r].cells = []
        while (n.rows[r].cells.length < cols)
            n.rows[r].cells.push({ text: "" })
        if (n.rows[r].cells.length > cols)
            n.rows[r].cells = n.rows[r].cells.slice(0, cols)
    }
}

function tableMinW(n) {
    return 8
}

function tableMinH(n) {
    return 8
}

function tableHomeRect(n, row, col) {
    var g = drawGeom(n)
    ensureTable(n)
    var rows = n.rows.length
    var cols = n.cols
    var idCol = !!n.idCol && cols > 1
    var idW = idCol ? Math.min(g.w * 0.32, Math.max(22, g.w * 0.22)) : 0
    var rest = Math.max(1, g.w - idW)
    var other = Math.max(1, idCol ? cols - 1 : cols)
    var colW = rest / other
    var rowH = g.h / Math.max(1, rows)
    var x = g.x
    var w = colW
    if (idCol) {
        if (col <= 0) {
            x = g.x
            w = idW
        } else {
            x = g.x + idW + (col - 1) * colW
            w = colW
        }
    } else {
        w = g.w / Math.max(1, cols)
        x = g.x + col * w
    }
    return { x: x, y: g.y + row * rowH, w: Math.max(8, w), h: Math.max(8, rowH) }
}

function tableGetCell(n, row, col) {
    if (!n || !n.rows || row < 0 || col < 0)
        return null
    if (row >= n.rows.length)
        return null
    var cells = n.rows[row].cells || []
    if (col >= cells.length)
        return null
    return cells[col]
}

function tableCellIsFree(n, row, col) {
    var c = tableGetCell(n, row, col)
    return !!(c && c.free)
}

function tableExtraAt(n, i) {
    if (!n || !n.extras || i < 0 || i >= n.extras.length)
        return null
    return n.extras[i]
}

function tablePartWorldRect(n, cell, fallback) {
    if (cell && cell.independent && cell.efw > 0 && cell.efh > 0) {
        return {
            x: fxToX(cell.efx || 0),
            y: fyToY(cell.efy || 0),
            w: fwToW(cell.efw),
            h: fhToH(cell.efh)
        }
    }
    return fallback
}

function writeTablePartRect(n, cell, x, y, w, h) {
    if (!cell)
        return
    w = Math.max(8, w)
    h = Math.max(8, h)
    var s = spaceRect()
    var pad = 4
    if (x < s.x + pad) x = s.x + pad
    if (y < s.y + pad) y = s.y + pad
    if (x + w > s.x + s.w - pad) x = Math.max(s.x + pad, s.x + s.w - pad - w)
    if (y + h > s.y + s.h - pad) y = Math.max(s.y + pad, s.y + s.h - pad - h)
    if (cell.independent) {
        cell.efx = xToFx(x)
        cell.efy = yToFy(y)
        cell.efw = w / Math.max(1, s.w)
        cell.efh = h / Math.max(1, s.h)
        return
    }
    var g = drawGeom(n)
    cell.ox = (x - g.x) / Math.max(1, g.w)
    cell.oy = (y - g.y) / Math.max(1, g.h)
    cell.cw = w / Math.max(1, g.w)
    cell.ch = h / Math.max(1, g.h)
}

function setTableCellIndependent(on) {
    var n = nodeAt(selectedId)
    if (!isTable(n) || !tableHasTarget())
        return
    var cell = tableCurrentCell(n)
    if (!cell)
        return
    var rc = tableCurrentRect(n)
    if (on) {
        cell.independent = true
        cell.free = true
        writeTablePartRect(n, cell, rc.x, rc.y, rc.w, rc.h)
    } else {
        cell.independent = false
        delete cell.efx
        delete cell.efy
        delete cell.efw
        delete cell.efh
        writeTablePartRect(n, cell, rc.x, rc.y, rc.w, rc.h)
    }
    bump()
}

function tableCellHandlesOn(n) {
    if (!interactive || !isTable(n) || isLocked(n) || !isSelected(n.id))
        return false
    if (tableExtra >= 0)
        return true
    var c = tableGetCell(n, tableRow, tableCol)
    return !!(c && c.free)
}

function tableExtraRect(n, i) {
    var e = tableExtraAt(n, i)
    var g = drawGeom(n)
    if (!e)
        return { x: g.x, y: g.y, w: 16, h: 16 }
    var follow = {
        x: g.x + (e.ox || 0) * g.w,
        y: g.y + (e.oy || 0) * g.h,
        w: Math.max(8, (e.cw > 0) ? e.cw * g.w : 16),
        h: Math.max(8, (e.ch > 0) ? e.ch * g.h : 16)
    }
    return tablePartWorldRect(n, e, follow)
}

function tableCurrentCell(n) {
    if (!n)
        return null
    if (tableExtra >= 0)
        return tableExtraAt(n, tableExtra)
    return tableGetCell(n, tableRow, tableCol)
}

function tableHasTarget() {
    return tableExtra >= 0 || (tableRow >= 0 && tableCol >= 0)
}

function tableCurrentRect(n) {
    if (tableExtra >= 0)
        return tableExtraRect(n, tableExtra)
    if (tableRow >= 0 && tableCol >= 0)
        return tableCellRect(n, tableRow, tableCol)
    return drawGeom(n)
}

function tableCellRect(n, row, col) {
    var home = tableHomeRect(n, row, col)
    var c = tableGetCell(n, row, col)
    if (!c || !c.free)
        return home
    var g = drawGeom(n)
    var follow = {
        x: g.x + (c.ox || 0) * g.w,
        y: g.y + (c.oy || 0) * g.h,
        w: Math.max(8, (c.cw > 0) ? c.cw * g.w : home.w),
        h: Math.max(8, (c.ch > 0) ? c.ch * g.h : home.h)
    }
    return tablePartWorldRect(n, c, follow)
}

function tableCellAt(n, mx, my) {
    if (!isTable(n))
        return { row: -1, col: -1, extra: -1 }
    ensureTable(n)
    var extras = n.extras || []
    var ei
    for (ei = extras.length - 1; ei >= 0; ei--) {
        var er = tableExtraRect(n, ei)
        if (mx >= er.x - 8 && mx <= er.x + er.w + 8 && my >= er.y - 8 && my <= er.y + er.h + 8)
            return { row: -1, col: -1, extra: ei }
    }
    var rows = n.rows.length
    var cols = n.cols
    var r
    var c
    for (r = rows - 1; r >= 0; r--) {
        for (c = cols - 1; c >= 0; c--) {
            if (!tableCellIsFree(n, r, c))
                continue
            var rc = tableCellRect(n, r, c)
            if (mx >= rc.x && mx <= rc.x + rc.w && my >= rc.y && my <= rc.y + rc.h)
                return { row: r, col: c, extra: -1 }
        }
    }
    var g = drawGeom(n)
    if (mx < g.x || my < g.y || mx > g.x + g.w || my > g.y + g.h)
        return { row: -1, col: -1, extra: -1 }
    var row = Math.floor((my - g.y) / Math.max(1, g.h / Math.max(1, rows)))
    var idCol = !!n.idCol && cols > 1
    var idW = idCol ? Math.min(g.w * 0.32, Math.max(22, g.w * 0.22)) : 0
    var lx = mx - g.x
    var col = 0
    if (idCol) {
        if (lx < idW)
            col = 0
        else
            col = 1 + Math.floor((lx - idW) / Math.max(1, (g.w - idW) / Math.max(1, cols - 1)))
    } else {
        col = Math.floor(lx / Math.max(1, g.w / Math.max(1, cols)))
    }
    if (row < 0) row = 0
    if (col < 0) col = 0
    if (row > rows - 1) row = rows - 1
    if (col > cols - 1) col = cols - 1
    return { row: row, col: col, extra: -1 }
}

function setTableCellFree(on) {
    var n = nodeAt(selectedId)
    if (!isTable(n) || !tableHasTarget())
        return
    ensureTable(n)
    var cell = tableCurrentCell(n)
    if (!cell)
        return
    var g = drawGeom(n)
    if (on) {
        if (!cell.free) {
            if (tableExtra >= 0) {
                if (!(cell.cw > 0)) cell.cw = 0.4
                if (!(cell.ch > 0)) cell.ch = 0.4
            } else {
                var home = tableHomeRect(n, tableRow, tableCol)
                cell.ox = (home.x - g.x) / Math.max(1, g.w)
                cell.oy = (home.y - g.y) / Math.max(1, g.h)
                cell.cw = home.w / Math.max(1, g.w)
                cell.ch = home.h / Math.max(1, g.h)
            }
        }
        cell.free = true
    } else {
        cell.free = false
        cell.ox = 0
        cell.oy = 0
        if (tableExtra < 0) {
            delete cell.cw
            delete cell.ch
        }
    }
    bump()
}

function toggleTableCellFree() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    var cell = tableCurrentCell(n)
    setTableCellFree(!(cell && cell.free))
}

function placeTableCell(where) {
    var n = nodeAt(selectedId)
    if (!isTable(n) || !tableHasTarget())
        return
    ensureTable(n)
    setTableCellFree(true)
    var cell = tableCurrentCell(n)
    if (!cell)
        return
    var rc = tableCurrentRect(n)
    var g = drawGeom(n)
    var x = rc.x
    var y = rc.y
    if (where === "left")
        x = g.x
    else if (where === "right")
        x = g.x + g.w - rc.w
    else if (where === "center")
        x = g.x + (g.w - rc.w) * 0.5
    else if (where === "top")
        y = g.y
    else if (where === "bottom")
        y = g.y + g.h - rc.h
    else if (where === "middle")
        y = g.y + (g.h - rc.h) * 0.5
    writeTablePartRect(n, cell, x, y, rc.w, rc.h)
    bump()
}

function spawnEmptyCell() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    var g = drawGeom(n)
    var src = tableCurrentRect(n)
    var cw = src.w / Math.max(1, g.w)
    var ch = src.h / Math.max(1, g.h)
    if (!(cw > 0)) cw = 0.4
    if (!(ch > 0)) ch = 0.4
    var ox = (src.x - g.x) / Math.max(1, g.w) + 12 / Math.max(1, g.w)
    var oy = (src.y - g.y) / Math.max(1, g.h) + 12 / Math.max(1, g.h)
    if (!n.extras)
        n.extras = []
    n.extras.push({
        text: "",
        free: true,
        independent: true,
        ox: ox,
        oy: oy,
        cw: cw,
        ch: ch,
        efx: xToFx(src.x + 12),
        efy: yToFy(src.y + 12),
        efw: src.w / Math.max(1, spaceRect().w),
        efh: src.h / Math.max(1, spaceRect().h)
    })
    tableExtra = n.extras.length - 1
    tableRow = -1
    tableCol = -1
    bump()
}

function deleteThisTableCell() {
    var n = nodeAt(selectedId)
    if (!isTable(n) || tableExtra < 0)
        return
    ensureTable(n)
    if (!n.extras || tableExtra >= n.extras.length)
        return
    n.extras.splice(tableExtra, 1)
    tableExtra = Math.min(tableExtra, n.extras.length - 1)
    bump()
}

function tableCellStyle(n, col) {
    var theme = (n && n.theme) ? String(n.theme) : "gremlin"
    var idCell = !!(n && n.idCol && col === 0)
    if (theme === "hollow")
        return { fill: "transparent", border: "#3F3F46", text: "#E4E4E7" }
    if (theme === "sheet") {
        if (idCell)
            return { fill: "#18181B", border: "#18181B", text: "#F4F4F5" }
        return { fill: "#E4E4E7", border: "#18181B", text: "#18181B" }
    }
    return { fill: "#18181B", border: "#3F3F46", text: "#E4E4E7" }
}

function tableCellText(n, row, col) {
    if (!n || !n.rows || row < 0 || col < 0)
        return ""
    if (row >= n.rows.length)
        return ""
    var cells = n.rows[row].cells || []
    if (col >= cells.length)
        return ""
    return cells[col].text || ""
}

function addTableRow(below) {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    var at = (tableRow >= 0) ? tableRow : n.rows.length - 1
    var row = emptyTableRow(n.cols)
    if (below)
        n.rows.splice(at + 1, 0, row)
    else
        n.rows.splice(Math.max(0, at), 0, row)
    tableRow = below ? at + 1 : Math.max(0, at)
    bump()
}

function deleteTableRow() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    if (n.rows.length <= 1)
        return
    var at = (tableRow >= 0) ? tableRow : n.rows.length - 1
    n.rows.splice(at, 1)
    tableRow = Math.min(at, n.rows.length - 1)
    bump()
}

function addTableCol(right) {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    var at = (tableCol >= 0) ? tableCol : n.cols - 1
    var insert = right ? at + 1 : Math.max(0, at)
    var r
    for (r = 0; r < n.rows.length; r++) {
        if (!n.rows[r].cells)
            n.rows[r].cells = []
        n.rows[r].cells.splice(insert, 0, { text: "" })
    }
    n.cols = n.cols + 1
    tableCol = insert
    bump()
}

function deleteTableCol() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    if (n.cols <= 1)
        return
    var at = (tableCol >= 0) ? tableCol : n.cols - 1
    var r
    for (r = 0; r < n.rows.length; r++) {
        if (n.rows[r].cells)
            n.rows[r].cells.splice(at, 1)
    }
    n.cols = n.cols - 1
    tableCol = Math.min(at, n.cols - 1)
    bump()
}

function toggleTableIdCol() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    ensureTable(n)
    n.idCol = !n.idCol
    bump()
}

function setTableTheme(name) {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    n.theme = name || "gremlin"
    bump()
}

function setTableFont(sz) {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    n.fontSize = sz
    bump()
}

function deleteTable() {
    var n = nodeAt(selectedId)
    if (!isTable(n))
        return
    deleteChip(n.id)
}

function beginTableRename(id, row, col, extra) {
    var n = nodeAt(id)
    if (!isTable(n))
        return
    ensureTable(n)
    renameId = id
    renameMember = -1
    tableRow = row
    tableCol = col
    tableExtra = (extra !== undefined && extra !== null) ? extra : -1
    if (tableExtra >= 0) {
        var ex = tableExtraAt(n, tableExtra)
        renameDraft = ex && ex.text ? ex.text : ""
    } else {
        renameDraft = tableCellText(n, row, col)
    }
    dragKind = ""
    Qt.callLater(function () {
        if (_nameEdit) {
            _nameEdit.forceActiveFocus()
            _nameEdit.selectAll()
        }
    })
    bump()
}

function applyTableCellResize(n, mx, my, handle, altOff) {
    var cell = tableCurrentCell(n)
    if (!cell)
        return
    cell.free = true
    if (!cell.independent)
        setTableCellIndependent(true)
    cell = tableCurrentCell(n)
    var p = snapEnt(mx, my, altOff)
    var x0 = rzX0
    var y0 = rzY0
    var x1 = rzX1
    var y1 = rzY1
    if (handle.indexOf("n") >= 0)
        y0 = p.y
    if (handle.indexOf("s") >= 0)
        y1 = p.y
    if (handle.indexOf("w") >= 0)
        x0 = p.x
    if (handle.indexOf("e") >= 0)
        x1 = p.x
    var nx = Math.min(x0, x1)
    var ny = Math.min(y0, y1)
    var nw = Math.max(8, Math.abs(x1 - x0))
    var nh = Math.max(8, Math.abs(y1 - y0))
    writeTablePartRect(n, cell, nx, ny, nw, nh)
}

function attachChipToTable(table, chip) {
    if (!table || !chip || isDraw(chip))
        return
    if (!table.packed)
        table.packed = []
    if (table.packed.indexOf(chip.id) < 0)
        table.packed.push(chip.id)
    chip.packId = table.id
    var fw = table.fw > 0 ? table.fw : 0.01
    var fh = table.fh > 0 ? table.fh : 0.01
    chip.packUx = ((chip.chipFx || 0) - (table.fx || 0)) / fw
    chip.packUy = ((chip.chipFy || 0) - (table.fy || 0)) / fh
}

function followTablePacked(table) {
    if (!isTable(table))
        return
    var i
    var ids = table.packed || []
    for (i = 0; i < ids.length; i++) {
        var q = nodeAt(ids[i])
        if (!q || isDraw(q))
            continue
        q.chipFx = (table.fx || 0) + (q.packUx || 0) * (table.fw || 0)
        q.chipFy = (table.fy || 0) + (q.packUy || 0) * (table.fh || 0)
    }
    var draws = table.packedDraw || []
    for (i = 0; i < draws.length; i++) {
        var d = nodeAt(draws[i])
        if (!isText(d) && !isDraw(d))
            continue
        d.fx = (table.fx || 0) + (d.packUx || 0) * (table.fw || 0)
        d.fy = (table.fy || 0) + (d.packUy || 0) * (table.fh || 0)
    }
}

function attachDrawToTable(table, draw) {
    if (!isTable(table) || !isDraw(draw) || draw.id === table.id)
        return
    if (!table.packedDraw)
        table.packedDraw = []
    if (table.packedDraw.indexOf(draw.id) < 0)
        table.packedDraw.push(draw.id)
    draw.packId = table.id
    var fw = table.fw > 0 ? table.fw : 0.01
    var fh = table.fh > 0 ? table.fh : 0.01
    draw.packUx = ((draw.fx || 0) - (table.fx || 0)) / fw
    draw.packUy = ((draw.fy || 0) - (table.fy || 0)) / fh
}

function tablePackOf(n) {
    if (!n)
        return null
    if (isTable(n) && tableIsPacked(n))
        return n
    if (n.packId) {
        var t = nodeAt(n.packId)
        if (isTable(t))
            return t
    }
    return null
}

function shiftIndependentParts(table, dFx, dFy) {
    if (!isTable(table) || (!dFx && !dFy))
        return
    function bump(cell) {
        if (!cell || !cell.independent)
            return
        cell.efx = (cell.efx || 0) + dFx
        cell.efy = (cell.efy || 0) + dFy
    }
    var extras = table.extras || []
    var i
    for (i = 0; i < extras.length; i++)
        bump(extras[i])
    var rows = table.rows || []
    var r
    var c
    for (r = 0; r < rows.length; r++) {
        var cells = rows[r] && rows[r].cells ? rows[r].cells : []
        for (c = 0; c < cells.length; c++)
            bump(cells[c])
    }
}

function moveTablePack(table, dFx, dFy) {
    if (!isTable(table) || isLocked(table))
        return
    table.fx = Math.max(0, Math.min(0.98, (table.fx || 0) + dFx))
    table.fy = Math.max(0, Math.min(0.98, (table.fy || 0) + dFy))
    shiftIndependentParts(table, dFx, dFy)
    followTablePacked(table)
}

function refreshChipPack(chip) {
    if (!chip || !chip.packId)
        return
    var table = nodeAt(chip.packId)
    if (!isTable(table))
        return
    attachChipToTable(table, chip)
}

function detachChipFromTable(chip) {
    if (!chip || !chip.packId)
        return
    var table = nodeAt(chip.packId)
    if (isTable(table) && table.packed) {
        var at = table.packed.indexOf(chip.id)
        if (at >= 0)
            table.packed.splice(at, 1)
    }
    delete chip.packId
    delete chip.packUx
    delete chip.packUy
}

function detachTablePacked(table) {
    if (!table)
        return
    var ids = (table.packed || []).slice()
    var i
    for (i = 0; i < ids.length; i++) {
        var q = nodeAt(ids[i])
        if (q) {
            delete q.packId
            delete q.packUx
            delete q.packUy
        }
    }
    table.packed = []
    var draws = (table.packedDraw || []).slice()
    for (i = 0; i < draws.length; i++) {
        var d = nodeAt(draws[i])
        if (d) {
            delete d.packId
            delete d.packUx
            delete d.packUy
        }
    }
    table.packedDraw = []
}

function tableIsPacked(n) {
    return !!(isTable(n) && ((n.packed && n.packed.length) || (n.packedDraw && n.packedDraw.length)))
}

function packTableFromSelection() {
    var ids = (selectedIds && selectedIds.length) ? selectedIds : (selectedId ? [selectedId] : [])
    var i
    for (i = 0; i < ids.length; i++) {
        var n = nodeAt(ids[i])
        if (tableIsPacked(n))
            return n
        if (n && n.packId) {
            var t = nodeAt(n.packId)
            if (tableIsPacked(t))
                return t
        }
    }
    return null
}
