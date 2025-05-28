function updateTable() {
  const tbody = document.querySelector("#measurementTable tbody");
  tbody.innerHTML = "";

  lines.forEach((line, index) => {
    const dx = line.end.x - line.start.x;
    const dy = line.end.y - line.start.y;
    const pixels = Math.sqrt(dx * dx + dy * dy);
    const realLength = pixels * scaleInchesPerPixel;

    // ➤ Update the line object with realLength
    line.realLength = realLength;

    const roomTypeHTML = roomTypeOptions.map(opt =>
      `<option value="${opt}" ${opt === line.roomType ? "selected" : ""}>${opt}</option>`
    ).join("");

    const designGoalHTML = designGoalOptions.map(opt =>
      `<option value="${opt}" ${opt === line.designGoal ? "selected" : ""}>${opt}</option>`
    ).join("");

    const wallMaterialHTML = wallMaterialOptions.map(opt =>
      `<option value="${opt}" ${opt === line.wallMaterial ? "selected" : ""}>${opt}</option>`
    ).join("");

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${index + 1}</td>
      <td><input type="text" value="${line.name}" onchange="renameLine(${index}, this.value)" style="width: 100px;" /></td>
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
      <td><button onclick="deleteLine(${index})">Delete</button></td>
    `;

    tbody.appendChild(row);
  });
}
