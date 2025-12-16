import React, { useEffect, useState } from "react";
import "./ReleaseNotes.css";

const ReleaseNotes = ({ onClose, unseenReleases = [] }) => {
  // unseenReleases: array of { version, notes }
  return (
    <div className="release-notes-modal">
      <div className="release-notes-content">
        <h2>Notas da Versão</h2>
        <div style={{ maxHeight: "55vh", overflowY: "auto" }}>
          {unseenReleases.length === 0 ? (
            <p>Sem atualizações novas.</p>
          ) : (
            unseenReleases.map((release) => (
              <div key={release.version} style={{ marginBottom: "1.5em" }}>
                <div
                  style={{ fontWeight: 600, color: "#7ec7ff", marginBottom: 4 }}
                >
                  Versão {release.version}
                </div>
                <ul>
                  {release.notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </div>
        <button onClick={onClose}>Fechar</button>
      </div>
    </div>
  );
};

export default ReleaseNotes;
