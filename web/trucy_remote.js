import { app } from "../../scripts/app.js";

// 执行核心逻辑：把 ID 解析出来，强制改变对应节点的 mode
const enforceTrucyLogic = (node) => {
    if (!node.widgets) return;
    
    let changed = false;

    // 1. 获取行为模式：2 为 Mute(静音)，4 为 Bypass(旁路)，0 为 Active(激活)
    const offWidget = node.widgets.find(w => w.name === "off_behavior");
    const offMode = (offWidget && offWidget.value === "Mute") ? 2 : 4;

    // ==========================================
    // 逻辑 1：5x5 遥控器
    // ==========================================
    if (node.comfyClass === "TrucyRemoteToggle5x5") {
        const groups = ["A", "B", "C", "D", "E"];
        for (const g of groups) {
            const idW = node.widgets.find(w => w.name === `${g}_Node_IDs`);
            const togW = node.widgets.find(w => w.name === `Toggle_${g}`);
            
            if (idW && togW && idW.value) {
                const isActive = !!togW.value;
                const targetMode = isActive ? 0 : offMode;
                
                const ids = String(idW.value).split(",").map(s => s.trim()).filter(s => s !== "");
                for (const idStr of ids) {
                    const targetNode = app.graph.getNodeById(Number(idStr));
                    if (targetNode && targetNode.mode !== targetMode) {
                        targetNode.mode = targetMode;
                        changed = true;
                    }
                }
            }
        }
    } 
    // ==========================================
    // 逻辑 2：5路主控矩阵 (5-way Mute/Bypass Nodes-Remote)
    // ==========================================
    else if (node.comfyClass === "TrucyMasterIntRouter") {
        const intWidget = node.widgets.find(w => w.name === "master_int");
        if (intWidget) {
            const currentMode = parseInt(intWidget.value, 10);
            
            const getIds = (name) => {
                const w = node.widgets.find(w => w.name === name);
                return (w && w.value) ? String(w.value).split(',').map(s => s.trim()).filter(s => s !== "") : [];
            };

            // 【修改点】：矩阵升级为 5 路
            const matrix = {
                1: getIds("Mode_1_Node_IDs"),
                2: getIds("Mode_2_Node_IDs"),
                3: getIds("Mode_3_Node_IDs"),
                4: getIds("Mode_4_Node_IDs"),
                5: getIds("Mode_5_Node_IDs") // 新增的第 5 路
            };

            // 【修改点】：汇总 5 路的所有 ID
            const allMatrixIds = [...new Set([
                ...matrix[1], ...matrix[2], ...matrix[3], ...matrix[4], ...matrix[5]
            ])];
            
            for (const idStr of allMatrixIds) {
                const targetNode = app.graph.getNodeById(Number(idStr));
                if (targetNode) {
                    let belongsToGroup = 0;
                    // 【修改点】：循环检测从 1 到 5
                    for (let g = 1; g <= 5; g++) {
                        if (matrix[g].includes(idStr)) {
                            belongsToGroup = g;
                            break;
                        }
                    }

                    if (belongsToGroup > 0) {
                        const targetMode = (belongsToGroup === currentMode) ? 0 : offMode;
                        if (targetNode.mode !== targetMode) {
                            targetNode.mode = targetMode;
                            changed = true;
                        }
                    }
                }
            }
        }
    }

    if (changed) {
        if (app.canvas) app.canvas.setDirty(true, true);
        if (app.graph) app.graph.change();
    }
};

const processNode = (node) => {
    if (!node.widgets) return;
    for (const w of node.widgets) {
        if (!w._trucy_hooked) {
            const origCb = w.callback;
            w.callback = function(val) {
                if (origCb) origCb.apply(this, arguments);
                enforceTrucyLogic(node);
            };
            w._trucy_hooked = true;
        }
    }
    enforceTrucyLogic(node);
};

app.registerExtension({
    name: "Trucy.RemoteControl",
    async nodeCreated(node) {
        if (node.comfyClass === "TrucyRemoteToggle5x5" || node.comfyClass === "TrucyMasterIntRouter") {
            const origDraw = node.onDrawForeground;
            node.onDrawForeground = function(ctx) {
                try { processNode(node); } catch(e) {}
                if (origDraw) origDraw.apply(this, arguments);
            };
            setTimeout(() => { try { processNode(node); } catch(e) {} }, 100);
        }
    },
    async afterConfigureGraph(missingNodeTypes) {
        if (app.graph && app.graph._nodes) {
            for (const node of app.graph._nodes) {
                if (node.comfyClass === "TrucyRemoteToggle5x5" || node.comfyClass === "TrucyMasterIntRouter") {
                    try { processNode(node); } catch(e) {}
                }
            }
        }
    }
});