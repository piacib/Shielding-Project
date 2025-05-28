function updateLineLength(index, newLength) {
  lines[index].realLength = parseFloat(newLength) || 0;
  recalculateBarrierThickness(); // Optional: if you're auto-calculating on update
}

function addManualLine() {
  if (event) event.preventDefault();
  const lengthInput = prompt(
    "Enter the real-world length (in inches) for the new line:"
  );

  if (lengthInput === null) return; // Cancelled
  const realLength = parseFloat(lengthInput);

  if (isNaN(realLength) || realLength <= 0) {
    alert("Please enter a valid positive number.");
    return;
  }
  print(realLength);
  const newLine = {
    start: { x: 0, y: realLength / scaleInchesPerPixel },
    end: { x: 0, y: 0 },
    name: `Line ${lines.length + 1}`,
    roomType: "Other",
    designGoal: "Uncontrolled",
    wallMaterial: "Lead",
    realLength: "---",
    requiredLead: "---",
  };

  lines.push(newLine);
  updateTable();
  updateTable();
  updateTable();
}

function renameLine(index, newName) {
  lines[index].name = newName;
  updateTable(); // Optional: re-render to apply duplicate highlighting
}

const image = new Image();
image.src = "{{ image_url }}";
let selectedHandle = null; // Will track { lineIndex, point: 'start' | 'end' }

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const confirmButton = document.getElementById("confirmButton");
const scaleOutput = document.getElementById("scaleOutput");
let pointA = { x: 100, y: 100 };
let pointB = { x: 300, y: 200 };
const radius = 8;
let draggingPoint = null;
let confirmed = false;
let scaleInchesPerPixel = 0;
let lines = [];
let isDrawingLine = false;
let tempStart = null;

image.onload = () => {
  canvas.width = image.width;
  canvas.height = image.height;
  drawCanvas();
};

const roomTypeOptions = [
  "Office,labs pharmacies, reception areas, waiting room,kid play area Patient Exam and Treatment Room",
  "Corridor, Patient Room, Employee Lounges, Staff Rest Room",
  "Corridor doors",
  "Public toilets, unattended vending areas, storage rooms, outdoor areas with seating, unattended waiting rooms, patient holding areas",
  "Outdoor areas with only transient pedestrian or vehicular traffic, unattended parking lots, vehicular drop off areas (unattended), attics, stairways, unattended elevators, janitor’s closets",
  "Other",
];
function getGlobalInputs() {
  const workload =
    parseFloat(document.getElementById("patientWorkload").value) || 0;
  const airKerma = parseFloat(document.getElementById("airKerma").value) || 0;
  return { workload, airKerma };
}
function submitToBackend() {
  const { workload, airKerma } = getGlobalInputs();
  console.log(workload);
  fetch("/calculate-thickness", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workload,
      airKerma,
      lines,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.lines) {
        lines = data.lines;
        updateTable();
      } else {
        alert("Calculation failed.");
      }
    })
    .catch((err) => {
      console.error("Error sending data to backend:", err);
      alert("Server error.");
    });
}

const designGoalOptions = ["Controlled", "Uncontrolled"];

const wallMaterialOptions = [
  "Lead",
  "Concrete",
  "Gypsum",
  "Steel",
  "Plate Glass",
  "Wood",
];

function updateRoomType(index, newType) {
  lines[index].roomType = newType;
  submitToBackend();
}

function drawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);

  lines.forEach(({ start, end, name }, index) => {
    drawLine(start, end, "green");
    drawHandle(start);
    drawHandle(end);

    // Calculate midpoint
    const midX = (start.x + end.x) / 2;
    const midY = (start.y + end.y) / 2;

    // Draw label
    ctx.fillStyle = "black";
    ctx.font = "bold 14px sans-serif";
    ctx.fillText(name || `Line ${index + 1}`, midX + 5, midY - 5);
  });

  if (!confirmed) {
    drawLine(pointA, pointB, "red");
    drawHandle(pointA);
    drawHandle(pointB);
  }
}

function drawLine(start, end, color) {
  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.lineTo(end.x, end.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

function drawHandle(point) {
  ctx.beginPath();
  ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = "blue";
  ctx.fill();
  ctx.strokeStyle = "white";
  ctx.stroke();
}

canvas.addEventListener("mousemove", (e) => {
  const x = e.offsetX;
  const y = e.offsetY;

  if (draggingPoint && !confirmed) {
    draggingPoint.x = x;
    draggingPoint.y = y;
    drawCanvas();
  } else if (isDrawingLine && confirmed) {
    drawCanvas();
    drawLine(tempStart, { x, y }, "orange");
  } else if (selectedHandle) {
    lines[selectedHandle.lineIndex][selectedHandle.point] = { x, y };
    drawCanvas();
    updateTable();
  }
});

canvas.addEventListener("mouseup", (e) => {
  if (isDrawingLine && confirmed) {
    lines.push({
      start: tempStart,
      end: { x: e.offsetX, y: e.offsetY },
      name: `Line ${lines.length + 1}`,
      roomType: "Other", // default value
      designGoal: "Uncontrolled", // default value
      wallMaterial: "Lead", // default value
    });
    isDrawingLine = false;
    tempStart = null;
    drawCanvas();
    updateTable();
    submitToBackend();
  }

  if (selectedHandle !== null) {
    selectedHandle = null;
    drawCanvas();
    updateTable();
    submitToBackend();
  }

  draggingPoint = null;
});

function isNearPoint(x, y, point) {
  return Math.hypot(point.x - x, point.y - y) < radius + 2;
}

confirmButton.addEventListener("click", () => {
  confirmed = true;
  draggingPoint = null;
  drawCanvas();
  document.getElementById("popupOverlay").style.display = "flex";
});

function closePopup() {
  document.getElementById("popupOverlay").style.display = "none";
  const feet = parseFloat(document.getElementById("feet").value) || 0;
  const inches = parseFloat(document.getElementById("inches").value) || 0;
  const totalInches = feet * 12 + inches;

  const dx = pointB.x - pointA.x;
  const dy = pointB.y - pointA.y;
  const pixelLength = Math.sqrt(dx * dx + dy * dy);

  if (totalInches > 0 && pixelLength > 0) {
    scaleInchesPerPixel = totalInches / pixelLength;
  }
}

document.getElementById("feet").addEventListener("input", updateScale);
document.getElementById("inches").addEventListener("input", updateScale);
function updateWallMaterial(index, newMaterial) {
  lines[index].wallMaterial = newMaterial;
  submitToBackend(); // Auto-trigger backend calculation
}

function updateDesignGoal(index, newGoal) {
  lines[index].designGoal = newGoal;
  submitToBackend(); // Auto-trigger backend calculation
}

function updateScale() {
  const feet = parseFloat(document.getElementById("feet").value) || 0;
  const inches = parseFloat(document.getElementById("inches").value) || 0;
  const totalInches = feet * 12 + inches;

  const dx = pointB.x - pointA.x;
  const dy = pointB.y - pointA.y;
  const pixelLength = Math.sqrt(dx * dx + dy * dy);

  if (totalInches > 0 && pixelLength > 0) {
    const scale = totalInches / pixelLength;
    scaleOutput.innerText = `Scale: ${scale.toFixed(4)} inches per pixel`;
  } else {
    scaleOutput.innerText = "";
  }
}
function getDuplicateNameRowColors(lines) {
  const nameCount = {};
  const colorMap = {};
  const colors = [
    "#fde2e2",
    "#e2f7e2",
    "#e2f0fd",
    "#fdf4e2",
    "#f0e2fd",
    "#e2fdf7",
    "#fce2fd",
    "#e2ecfc",
  ];

  // Count name frequencies
  lines.forEach((line) => {
    nameCount[line.name] = (nameCount[line.name] || 0) + 1;
  });

  let colorIndex = 0;
  for (const name in nameCount) {
    if (nameCount[name] > 1) {
      colorMap[name] = colors[colorIndex % colors.length];
      colorIndex++;
    }
  }

  return colorMap;
}

function updateTable() {
  const nameColorMap = getDuplicateNameRowColors(lines);
  const tbody = document.querySelector("#measurementTable tbody");
  tbody.innerHTML = "";

  lines.forEach((line, index) => {
    const dx = line.end.x - line.start.x;
    const dy = line.end.y - line.start.y;
    const pixels = Math.sqrt(dx * dx + dy * dy);
    const realLength = pixels * scaleInchesPerPixel;
    line.realLength = realLength;

    const roomTypeHTML = roomTypeOptions
      .map(
        (opt) =>
          `<option value="${opt}" ${
            opt === line.roomType ? "selected" : ""
          }>${opt}</option>`
      )
      .join("");

    const designGoalHTML = designGoalOptions
      .map(
        (opt) =>
          `<option value="${opt}" ${
            opt === line.designGoal ? "selected" : ""
          }>${opt}</option>`
      )
      .join("");

    const wallMaterialHTML = wallMaterialOptions
      .map(
        (opt) =>
          `<option value="${opt}" ${
            opt === line.wallMaterial ? "selected" : ""
          }>${opt}</option>`
      )
      .join("");

    const row = document.createElement("tr");
    if (nameColorMap[line.name]) {
      row.style.backgroundColor = nameColorMap[line.name];
    }

    row.innerHTML = `
         <td>${index + 1}</td>
         <td>
           <input type="text" value="${
             line.name
           }" onchange="renameLine(${index}, this.value)" style="width: 100px;" />
         </td>
         
         <td>
           <select onchange="updateRoomType(${index}, this.value)" style="max-width: 250px;">
             ${roomTypeHTML}
           </select>
         </td>
         <td>
           <select onchange="updateDesignGoal(${index}, this.value)">
             ${designGoalHTML}
           </select>
         </td>
         <td>
           <select onchange="updateWallMaterial(${index}, this.value)">
             ${wallMaterialHTML}
           </select>
         </td>
         <td>${realLength.toFixed(2)} in</td>
         <td>${
           line.requiredThickness
             ? `${line.requiredThickness.toFixed(2)} mm`
             : "-"
         }</td>
         <td>${line.requiredLead ? `${line.requiredLead}` : "-"}</td>
         
         <td><button onclick="deleteLine(${index})">Delete</button></td>
         `;

    tbody.appendChild(row);
  });
}

function deleteLine(index) {
  lines.splice(index, 1); // Remove the line from the array
  drawCanvas(); // Redraw without the deleted line
  updateTable(); // Rebuild the table
}

canvas.addEventListener("mousedown", (e) => {
  const x = e.offsetX;
  const y = e.offsetY;

  if (!confirmed) {
    if (isNearPoint(x, y, pointA)) draggingPoint = pointA;
    else if (isNearPoint(x, y, pointB)) draggingPoint = pointB;
  } else {
    for (let i = 0; i < lines.length; i++) {
      if (isNearPoint(x, y, lines[i].start)) {
        selectedHandle = { lineIndex: i, point: "start" };
        return;
      }
      if (isNearPoint(x, y, lines[i].end)) {
        selectedHandle = { lineIndex: i, point: "end" };
        return;
      }
    }
    tempStart = { x, y };
    isDrawingLine = true;
  }
});
