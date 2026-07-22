import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "Comfy.TrucyNodes.Remote",
    async nodeCreated(node) {
        if (node.comfyClass === "TrucyMasterIntRouter") {
            const updateNodes = () => {
                if (!node.widgets) return;

                const masterIntWidget = node.widgets.find(w => w.name === "master_int");
                const offBehaviorWidget = node.widgets.find(w => w.name === "off_behavior");
                
                if (!masterIntWidget || !offBehaviorWidget) return;

                const currentMode = masterIntWidget.value;
                
                // Mute对应的数值是2, Bypass是4 (ComfyUI底层逻辑)
                const offMode = offBehaviorWidget.value === "Mute" ? 2 : 4;

                // 辅助函数：安全地读取输入框并转为数组
                const getIds = (widgetName) => {
                    const w = node.widgets.find(w => w.name === widgetName);
                    if (!w || !w.value) return [];
                    return w.value.split(/[,，\s]+/).map(s => s.trim()).filter(s => s !== "");
                };

                const matrix = {
                    1: getIds("Mode_1_Node_IDs"),
                    2: getIds("Mode_2_Node_IDs"),
                    3: getIds("Mode_3_Node_IDs"),
                    4: getIds("Mode_4_Node_IDs"),
                    5: getIds("Mode_5_Node_IDs")
                };

                let changed = false;

                // 把5个框里出现过的所有 ID 汇总，并去重
                const allMatrixIds = [...new Set([
                    ...matrix[1], ...matrix[2], ...matrix[3], ...matrix[4], ...matrix[5]
                ])];
                
                for (const idStr of allMatrixIds) {
                    const targetNode = app.graph.getNodeById(Number(idStr));
                    if (targetNode) {
                        // 核心判断：当前这个 ID，是否包含在“目前选中的 INT 模式”对应的框里？
                        const shouldBeActive = matrix[currentMode] && matrix[currentMode].includes(idStr);
                        
                        // 如果在当前模式里，就激活(0)；如果不在，就关闭(offMode)
                        const targetMode = shouldBeActive ? 0 : offMode;
                        
                        if (targetNode.mode !== targetMode) {
                            targetNode.mode = targetMode;
                            changed = true;
                        }
                    }
                }

                if (changed) {
                    app.graph.setDirtyCanvas(true, true);
                }
            };

            // 监听所有控件的变化，只要改了任意一个，就触发检查
            const widgetNamesToWatch = [
                "master_int", 
                "off_behavior", 
                "Mode_1_Node_IDs", 
                "Mode_2_Node_IDs", 
                "Mode_3_Node_IDs", 
                "Mode_4_Node_IDs", 
                "Mode_5_Node_IDs"
            ];
            
            node.widgets.forEach(w => {
                if (widgetNamesToWatch.includes(w.name)) {
                    const origCallback = w.callback;
                    w.callback = function() {
                        if (origCallback) origCallback.apply(this, arguments);
                        updateNodes();
                    };
                }
            });

            // 执行时也刷新一次
            const origOnExecuted = node.onExecuted;
            node.onExecuted = function(message) {
                if (origOnExecuted) origOnExecuted.apply(this, arguments);
                updateNodes();
            };

            // 清理逻辑：如果把这个控制器节点删了，把受它控制的节点全都恢复成“激活”状态
            const origOnRemoved = node.onRemoved;
            node.onRemoved = function() {
                if (origOnRemoved) origOnRemoved.apply(this, arguments);
                
                const getIds = (widgetName) => {
                    const w = node.widgets.find(w => w.name === widgetName);
                    if (!w || !w.value) return [];
                    return w.value.split(/[,，\s]+/).map(s => s.trim()).filter(s => s !== "");
                };

                const allIds = [...new Set([
                    ...getIds("Mode_1_Node_IDs"),
                    ...getIds("Mode_2_Node_IDs"),
                    ...getIds("Mode_3_Node_IDs"),
                    ...getIds("Mode_4_Node_IDs"),
                    ...getIds("Mode_5_Node_IDs")
                ])];

                let changed = false;
                for (const idStr of allIds) {
                    const targetNode = app.graph.getNodeById(Number(idStr));
                    if (targetNode && targetNode.mode !== 0) {
                        targetNode.mode = 0; 
                        changed = true;
                    }
                }
                
                if (changed) {
                    app.graph.setDirtyCanvas(true, true);
                }
            };

            // 初始化：等待半秒，等 ComfyUI 画布加载完，再执行第一次排查
            setTimeout(updateNodes, 500);
        }
    }
});