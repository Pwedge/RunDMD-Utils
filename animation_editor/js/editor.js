// Used https://codepen.io/seipy/pen/ZEYzBQz as a starting point

// NOTE: Color index 0xa in the JSON data is transparency
const trans_idx = 10;
const colors = ['#000000', '#700000', '#7b0000', '#860000', '#910000', '#9c0000', '#a70000', '#b20000', '#bd0000', '#c80000', '#e0e0e0', '#d30000', '#de0000', '#e90000', '#f40000', '#ff0000'];


const fileInput = document.querySelector('#file-button');
const saveButton = document.querySelector('#save-button');
const playButton = document.querySelector('#play-button');

const introTransition = document.querySelector("#intro-transition");
const outroTransition = document.querySelector("#outro-transition");
const clockType = document.querySelector("#clock-type");
const clockSize = document.querySelector("#clock-size");
const clockStart = document.querySelector('#clock-start-frame');
const clockEnd = document.querySelector('#clock-end-frame');
const clockX = document.querySelector('#clock-position-x');
const clockY = document.querySelector('#clock-position-y');

const frameNumber = document.querySelector('#frame-number');
const frameDuration = document.querySelector('#frame-duration');
const dropFrameBack = document.querySelector('#drop-frame-back');
const dropFrameForward = document.querySelector('#drop-frame-forward');

const drawMode = document.querySelectorAll('.draw-mode');
const historyUndo = document.querySelector('#history-undo');
const historyRedo = document.querySelector('#history-redo');
const colorChoices = document.querySelectorAll('.color-choice');
const pixelCanvas = document.querySelector('#pixel-canvas');

var clockData;
var aniData;
var cur_color;
var frame_history = [];
var frame_history_idx = -1;

function loadAnimationFile() {
    let file = fileInput.files[0];
    let fr = new FileReader();
    fr.onload = receivedText;
    fr.readAsText(file);
    
    function receivedText(e) {
        let lines = e.target.result;
        aniData = JSON.parse(lines);
        frameNumber.setAttribute('min', '0');
        frameNumber.setAttribute('max', (aniData['frames'].length - 1).toString());
        frameNumber.value = 0;
        getHeaderOptions();
    }
}

function saveAnimationFile() {
    const a = document.createElement('a');
    var cur_file = fileInput.files[0].name;
    var cur_file_ext = cur_file.split('.').pop();
    var cur_file_name = cur_file.split('/').pop().replace('.' + cur_file_ext, '');
    var new_file = cur_file_name + '-new.' + cur_file_ext;
    
    a.href = URL.createObjectURL(new Blob([JSON.stringify(aniData, null, 2)], {
        type: "text/plain"
    }));
    
    /* Update frame numbers */
    for (let i = 0; i < aniData['frames'].length; i++) {
        aniData['frames'][i]['frame_num'] = i;
    }
    
    a.setAttribute('download', new_file);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function playAnimation() {
    let running_dur = 0;
    let intro = 0;
    let outro = 0;
    
    clearHistory();
    
    if (aniData['header']['intro_transition'] == 'Enable') {
        intro = 1;
    }
    if (aniData['header']['outro_transition'] == 'Enable') {
        outro = 1;
    }
    
    running_dur += showClock(intro, 0, 0);
    
    frameNumber.value = 0;
    getFrame(frameNumber.value);
    for (let frame_num = 1; frame_num < aniData['frames'].length; frame_num++) {
        running_dur += aniData['frames'][frame_num - 1]['duration'];
        (function (i, t) {
            setTimeout(function() {
                frameNumber.value = i;
                getFrameOptions(frameNumber.value);
            }, t);
        })(frame_num, running_dur);
    }
    
    showClock(0, outro, running_dur);
}


function getHeaderOptions() {
    let ani_header = aniData['header'];
    
    introTransition.value = ani_header['intro_transition'];
    outroTransition.value = ani_header['outro_transition'];
    clockType.value = ani_header['clock_type'];
    clockSize.value = ani_header['clock_size'];
    clockStart.value = ani_header['clock_start_frame'];
    clockEnd.value = ani_header['clock_end_frame'];
    clockX.value = ani_header['clock_position_x'];
    clockY.value = ani_header['clock_position_y'];
    
    getFrameOptions(frameNumber.value);
}

function setHeaderOption(ele) {
    let intVal = parseInt(ele.value);
    
    if (!isNaN(intVal)) {
        aniData['header'][ele.id.replaceAll('-', '_')] = intVal;
    } else {
        aniData['header'][ele.id.replaceAll('-', '_')] = ele.value;
    }
    getHeaderOptions();
}

function _setHeaderOption(e) {
    setHeaderOption(e.target);
}


function getFrameOptions(frame_num) {
    let frame_data = aniData['frames'][frame_num];
    
    frameDuration.value = frame_data['duration'];
    
    getFrame(frame_num);
}

function setFrameOption(ele) {
    let frame_num = frameNumber.value;
    let intVal = parseInt(ele.value);
    
    if (ele.id == 'frame-number') {
        /* Don't modify data structure */
    } else if (!isNaN(intVal)) {
        aniData['frames'][frame_num][ele.id.replaceAll('-', '_')] = intVal;
    } else {
        aniData['frames'][frame_num][ele.id.replaceAll('-', '_')] = ele.value;
    }
    getFrameOptions(frame_num);
}

function _setFrameOption(e) {
    setFrameOption(e.target);
}


function getFrame(frame_num) {
    let frame_data = aniData['frames'][frame_num];
    let frame_pixels = frame_data['bitmap'];
    
    for (let y = 0; y < 32; y++) {
        let row = frame_pixels[y];
        for (let x = 0; x < 128; x++) {
            let pixel_hex = row.charAt(1 + x);
            let pixel_color = colors[parseInt(pixel_hex, 16)];
            displayPixel(frame_num, x, y, pixel_color);
        }
    }
}

function showClock(transition_in, transition_out, start_time) {
    let frame_ms = 25;
    let frame_pixels = clockData['frames'][0]['bitmap'];
    let start_row = 0;
    let row_inc = 0
    let num_frames = 32;
    let running_dur = start_time;
    
    if (transition_in) {
        row_inc = 1;
    } else if (transition_out) {
        start_row = 31;
        row_inc = -1;
    }
    
    for (let frame_num = 0; frame_num < num_frames; frame_num++) {
        running_dur += frame_ms;
        (function (o, t) {
            setTimeout(function() {
                let row = NaN;
                let pixel_idx = NaN;
                for (let y = 0; y < 32; y++) {
                    if (y + o < 32) { 
                        row = frame_pixels[y + o];
                    }
                    for (let x = 0; x < 128; x++) {
                        let id_str = 'pixel_' + x.toString() + '_' + y.toString();
                        let ele = document.getElementById(id_str);
                        
                        if (y + o < 32) {
                            pixel_idx = parseInt(row.charAt(1 + x), 16);
                            if (pixel_idx == 10) {
                                pixel_idx = 0;
                            }
                        } else {
                            pixel_idx = 0;
                        }
                        ele.style.backgroundColor = colors[pixel_idx];
                    }
                }
            }, t);
        })(start_row + frame_num * row_inc, running_dur);
    }
    
    return running_dur;
}

function clearHistory() {
    frame_history = [];
    frame_history_idx = -1;
}

function changeHistory(dir) {
    frame_data = aniData['frames'][frameNumber.value];
    if (dir > 0 && frame_history_idx < frame_history.length - 1) {
        /* Move forward */
        frame_history_idx++;
        frame_data['bitmap'] = frame_history[frame_history_idx];
    } else if (dir < 0 && frame_history_idx > 0) {
        if (frame_history_idx == frame_history.length - 1) {
            /* Capture current frame before undo */
            addUndo();
        }
        /* Move backward */
        frame_history_idx--;
        frame_data['bitmap'] = frame_history[frame_history_idx];
    }
    getFrame(frameNumber.value);
}

function addUndo() { 
    frame_history = frame_history.slice(0, frame_history_idx + 1);
    frame_history.push(JSON.parse(JSON.stringify(aniData['frames'][frameNumber.value]['bitmap'])));
    frame_history_idx = frame_history.length - 1;
}

function undoHistory() {
    changeHistory(-1);
}

function redoHistory() {
    changeHistory(1);
}


/* Helpers */
function displayPixel(frame_num, x, y, color) {
    let overlay_pixel = color;
    let underlay_pixel = color;
    let final_pixel = colors[trans_idx];
    let id_str = 'pixel_' + x.toString() + '_' + y.toString();
    let ele = document.getElementById(id_str);
    let ani_header = aniData['header'];
    
    if (ani_header['clock_start_frame'] <= frame_num &&
            ani_header['clock_end_frame'] >= frame_num) {
        /* Clock may need to be displayed */
        if (ani_header['clock_size'] == 'ClockLarge') {
            clock_x = x;
            clock_y = y;
            if (ani_header['clock_type'] == 'ClockOnTop') {
                overlay_pixel = colors[parseInt(clockData['frames'][0]['bitmap'][clock_y].charAt(1 + clock_x), 16)];
            } else if (ani_header['clock_type'] == 'ClockBehind') {
                underlay_pixel = colors[parseInt(clockData['frames'][0]['bitmap'][clock_y].charAt(1 + clock_x), 16)];
            }
        } else if (ani_header['clock_size'] == 'ClockSmall') {
            clock_x = x - ani_header['clock_position_x'];
            clock_y = y - ani_header['clock_position_y'];
            if (clock_x >= 0 && clock_y >= 0) {
                if (ani_header['clock_type'] == 'ClockOnTop') {
                    overlay_pixel = colors[parseInt(clockData['frames'][1]['bitmap'][clock_y].charAt(1 + clock_x), 16)];
                } else if (ani_header['clock_type'] == 'ClockBehind') {
                    underlay_pixel = colors[parseInt(clockData['frames'][1]['bitmap'][clock_y].charAt(1 + clock_x), 16)];
                }
            }
        }
    }
    
    /* Merge pixel */
    if (overlay_pixel != colors[trans_idx]) {
        final_pixel = overlay_pixel;
    } else if (underlay_pixel != colors[trans_idx]) {
        final_pixel = underlay_pixel;
    }
    
    /* Present it */
    ele.style.backgroundColor = final_pixel;
}

function makeGrid() {
    let gridHeight = 32;
    let gridWidth = 128;
    // If grid already present, clears any cells that have been filled in
    while (pixelCanvas.firstChild) {
        pixelCanvas.removeChild(pixelCanvas.firstChild);
    }
    // Creates rows and cells
    for (let i = 0; i < gridHeight; i++) {
        let gridRow = document.createElement('tr');
        pixelCanvas.appendChild(gridRow);
        for (let j = 0; j < gridWidth; j++) {
            let gridCell = document.createElement('td');
            let id_str = 'pixel_' + j.toString() + '_' + i.toString();
            gridCell.setAttribute('id', id_str);
            gridRow.appendChild(gridCell);
        }
    }
}

function setColor(ele) {
    // Data structure update
    let color_idx = document.querySelector('.chosen-color').id.split('_')[1];
    let x_coord = parseInt(ele.id.split('_')[1]);
    let y_coord = parseInt(ele.id.split('_')[2]);
    let frame_num = frameNumber.value;
    let frame_line = aniData['frames'][frame_num]['bitmap'][y_coord].split('');
    frame_line[x_coord + 1] = color_idx;
    aniData['frames'][frame_num]['bitmap'][y_coord] = frame_line.join('');
    
    // On screen update
    displayPixel(frame_num, x_coord, y_coord, cur_color);
}

let border_pixels = [];
let checked_pixels = {};
function _findBorderPixels(x, y, target_color_idx) {
    if (x < 0 || x >= 128 || y < 0 || y >= 32) {
        return 0;
    }
    
    let x_y_str = [x, y].join('_');
    if (x_y_str in checked_pixels) {
        return checked_pixels[x_y_str];
    }
    checked_pixels[x_y_str] = 0;
    
    let frame_line = aniData['frames'][frameNumber.value]['bitmap'][y].split('');
    if (frame_line[x + 1] != target_color_idx && frame_line[x + 1] != 0) {
        /* Caller needs to be informed that the current pixel is part of a boundary */
        checked_pixels[x_y_str] = 1;
        return 1;
    }
    
    let is_bordered = 0;
    let check_pixels = [[x, y - 1], [x, y + 1], [x - 1, y], [x + 1, y]];
    for (let check_pixel of check_pixels) {
        is_bordered += _findBorderPixels(check_pixel[0], check_pixel[1], target_color_idx);
    }
    
    if (is_bordered) {
        border_pixels.push([x, y]);
    }
    
    return 0;
}

function drawBorder(x, y) {
    if (x < 0 || x >= 128 || y < 0 || y >= 32) {
        return;
    }
    
    let target_color_idx = aniData['frames'][frameNumber.value]['bitmap'][y][x + 1];
    border_pixels = [];
    checked_pixels = {};
    
    _findBorderPixels(x, y, target_color_idx);
    
    for (border_pixel of border_pixels) {
        let this_x = border_pixel[0];
        let this_y = border_pixel[1];
        let frame_line = aniData['frames'][frameNumber.value]['bitmap'][this_y].split('');
        frame_line[this_x + 1] = '0';
        aniData['frames'][frameNumber.value]['bitmap'][this_y] = frame_line.join('');
    }
}

function fillPixels(x, y, target_color_idx) {
    if (x < 0 || x >= 128 || y < 0 || y >= 32) {
        return;
    }
    
    let new_color_idx = document.querySelector('.chosen-color').id.split('_')[1];
    let my_color_idx = aniData['frames'][frameNumber.value]['bitmap'][y][x + 1];
    if (my_color_idx != target_color_idx || my_color_idx == new_color_idx) {
        return;
    }
    
    /* Only update data structure */
    let frame_line = aniData['frames'][frameNumber.value]['bitmap'][y].split('');
    frame_line[x + 1] = new_color_idx;
    aniData['frames'][frameNumber.value]['bitmap'][y] = frame_line.join('');
    
    let check_pixels = [[x, y - 1], [x, y + 1], [x - 1, y], [x + 1, y]];
    for (let check_pixel of check_pixels) {
        let this_x = check_pixel[0];
        let this_y = check_pixel[1];
        
        fillPixels(this_x, this_y, target_color_idx);
    }
}

// Enables color dragging with selected color (code for filling in single cell is above). (No click on 'draw' mode needed; this is default mode)
let down = false; // Tracks whether or not mouse pointer is pressed

// Listens for mouse pointer press and release on grid. Changes value to true when pressed', but sets it back to false as soon as released
pixelCanvas.addEventListener('mousedown', function(e) {
    addUndo();
    
    down = true;
    pixelCanvas.addEventListener('mouseup', function() {
        down = false;
    });
    // Ensures cells won't be colored if grid is left while pointer is held down
    pixelCanvas.addEventListener('mouseleave', function() {
        down = false;
    });
    
    let fill_mode = 0;
    let border_mode = 0;
    for (let i = 0; i < drawMode.length; i++) {
        if (drawMode[i].checked && drawMode[i].value == 'fill-mode') {
            down = false;
            fill_mode = 1;
            break;
        } else if (drawMode[i].checked && drawMode[i].value == 'border-mode') {
            down = false;
            border_mode = 1;
            break;
        }
    }
    
    if (fill_mode || border_mode) {
        let ele = e.target;
        let x = parseInt(ele.id.split('_')[1]);
        let y = parseInt(ele.id.split('_')[2]);
        let target_color_idx = aniData['frames'][frameNumber.value]['bitmap'][y][x + 1];
        fillPixels(x, y, target_color_idx);
        
        if (border_mode) {
            console.log("about to call drawBorder");
            drawBorder(x, y);
        }
        
        getFrame(frameNumber.value);
    } else {
        setColor(e.target);
        
        pixelCanvas.addEventListener('mouseover', function(e) {
            // 'color' defined here rather than globally so JS checks whether user has changed color with each new mouse press on cell
            //const color = document.querySelector('.color-picker').value;
            // While mouse pointer is pressed and within grid boundaries', fills cell with selected color. Inner if statement fixes bug that fills in entire grid
                if (down) {
                // 'TD' capitalized because element.tagName returns upper case for DOM trees that represent HTML elements
                if (e.target.tagName === 'TD') {
                    setColor(e.target);
                }
            }
        });
    }
});

function frameDurationFunc () {
    aniData['frames'][frameNumber.value]['duration'] = parseInt(frameDuration.value);
}

function dropFrameFunc(dir) {
    let cur_frame = parseInt(frameNumber.value);
    let target_frame = cur_frame + dir;
    
    if (target_frame < 0 || target_frame > aniData['frames'].length) {
        return;
    }
    
    /* Add to target frame duration */
    aniData['frames'][target_frame]['duration'] += aniData['frames'][cur_frame]['duration'];
    
    /* Nuke the frame */
    aniData['frames'].splice(cur_frame, 1);
    
    /* Re-render */
    if (dir > 0) {
        frameNumber.value = cur_frame;
        getFrameOptions(cur_frame);
    } else {
        frameNumber.value = target_frame;
        getFrameOptions(target_frame);
    }
}

function dropFrameBackFunc() {
    dropFrameFunc(-1);
}

function dropFrameForwardFunc() {
    dropFrameFunc(1);
}

fileInput.addEventListener('input', loadAnimationFile);
saveButton.addEventListener('click', saveAnimationFile);
playButton.addEventListener('click', playAnimation);

introTransition.addEventListener('input', _setHeaderOption);
outroTransition.addEventListener('input', _setHeaderOption);
clockType.addEventListener('input', _setHeaderOption);
clockSize.addEventListener('input', _setHeaderOption);
clockStart.addEventListener('input', _setHeaderOption);
clockEnd.addEventListener('input', _setHeaderOption);
clockX.addEventListener('input', _setHeaderOption);
clockY.addEventListener('input', _setHeaderOption);

frameNumber.addEventListener('input', _setFrameOption);
frameDuration.addEventListener('input', frameDurationFunc);
dropFrameBack.addEventListener('click', dropFrameBackFunc);
dropFrameForward.addEventListener('click', dropFrameForwardFunc);

historyUndo.addEventListener('click', undoHistory);
historyRedo.addEventListener('click', redoHistory);

document.onkeydown = function(e) {
    if (e.keyCode == '38') {
        frameNumber.value = parseInt(frameNumber.value) + 1;
        getFrameOptions(parseInt(frameNumber.value));
    } else if (e.keyCode == '40') {
        frameNumber.value = parseInt(frameNumber.value) - 1;
        getFrameOptions(parseInt(frameNumber.value));
    }
};

document.addEventListener('DOMContentLoaded', function() {
    var j = 1;
    for (var i = 0; i < colorChoices.length; i++) {
        if (i == trans_idx) {
            colorChoices[0].style.backgroundColor = colors[i];
            colorChoices[0].id = 'color_' + i.toString(16);
            colorChoices[0].classList.add('chosen-color');
            cur_color = colors[i];
        } else {
            colorChoices[j].style.backgroundColor = colors[i];
            colorChoices[j++].id = 'color_' + i.toString(16);
        }
        colorChoices[i].addEventListener('click', function(e) {
            var prev_selected = document.querySelector('.chosen-color');
            prev_selected.classList.remove('chosen-color');
            e.target.classList.add('chosen-color');
            cur_color = e.target.style.backgroundColor;
        });
    }
    
    makeGrid();
    
    clockData = 
        {
          "frames": [
            {
              "bitmap": [
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaa0000aaaaaa0000000000aaaaaaa0000000000aa0000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaaa0ffffffffff0aaaaa0ffffffffff00ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaa00ffff0aaa0ffffffffffff0aaa0ffffffffffff0ffff0aaa0000aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffff0aaa0ffffffffffff0aaa0ffffffffffff0ffff0aa0ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffff0aaa0ffffffffffff00000ffffffffffff0ffff0aa0ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffff0aaa0ffff0000ffff0fff0ffff0000ffff0ffff0aa0ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffff0aaaa0000aaa0ffff0fff00000aaa0ffff0ffff0aa0ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaa00ffff0aaaaa0000000ffff0fff0aaaa0000ffff0ffff0000ffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaaa0fffffffffff0000aaaa0ffffffff0ffffffffffff0aaa00000aa00aaaa00aaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaa0ffffffffffff0aaaaaaa0fffffff00ffffffffffff0aa0fffff00ff0aa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaa0ffffffffffff0aaaaaaa0fffffff00ffffffffffff0a0fffffff0fff00fff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaa0fffffffffff0a000aaaa0ffffffff0ffffffffffff0a0ff000ff0ffffffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaa0ffff0000000a0fff0aaaa0000ffff000000000ffff0a0ff000ff0ffffffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaa0ffff0aaa0ffff0aaaaaaa0fff00000aaa0ffff0aaaaaaa0ffff0a0fffffff0ff0ff0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaa00ffff00aa0ffff000000000fff0ffff0000ffff0aaaaaaa0ffff0a0fffffff0ff0000ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffffff0a0ffffffffffff00000ffffffffffff0aaaaaaa0ffff0a0ff000ff0ff0aa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffffff0a0ffffffffffff0aaa0ffffffffffff0aaaaaaa0ffff0a0ff0a0ff0ff0aa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffffff0a0ffffffffffff0aaa0ffffffffffff0aaaaaaa0ffff0a0ff0a0ff0ff0aa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaa0ffffffff0a0ffffffffffff0aaaa0ffffffffff0aaaaaaaa0ffff0a0ff0a0ff0ff0aa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaa00000000aaa000000000000aaaaaa0000000000aaaaaaaaaa0000aaa00aaa00a00aaaa00aaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|"
              ]
            },
            {
              "bitmap": [
                "|aaaa00aaaa00000aaaaaa00000aa00aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0aa0fffff0aaaa0fffff00ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aa0fff0a0fffffff0000fffffff0ff0a00aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aa0fff0a0ff000ff0ff0ff000ff0ff00ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0aa00000ff0ff000a00ff0ff00ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0aa0ffffff000aaa0fff00ff00ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0a0ffffff0a00aaa0fff00fffffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0a0ff0000a0ff000a00ff0fffffff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0ff0a0ff000000ff0ff000ff00000ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aa0ffff00fffffff0000fffffff0aaa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aa0ffff00fffffff0aaa0fffff0aaaa0ff0aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaa0000aa0000000aaaaa00000aaaaaa00aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|",
                "|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|"
              ]
            }
          ]
        };
});