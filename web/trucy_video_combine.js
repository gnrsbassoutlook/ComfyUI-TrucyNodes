import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { setWidgetConfig } from "../../extensions/core/widgetInputs.js";
import { applyTextReplacements } from "../../scripts/utils.js";

const NODE_NAME = "TrucyVideoCombine";

function chainCallback(object, property, callback) {
    if (!object) return;
    if (property in object && object[property]) {
        const original = object[property];
        object[property] = function () {
            const result = original.apply(this, arguments);
            const callbackResult = callback.apply(this, arguments);
            return callbackResult ?? result;
        };
    } else {
        object[property] = callback;
    }
}

const convDict = {
    [NODE_NAME]: [
        "frame_rate",
        "loop_count",
        "filename_prefix",
        "format",
        "pingpong",
        "save_output",
        "custom_path",
    ],
};

function roundVhsNumber(value, precision) {
    const fixed = Number(value).toFixed(precision);
    const dot = fixed.indexOf(".");
    if (dot < 0) return fixed;
    let end = fixed.length - 1;
    while (end > dot && fixed[end] === "0") end--;
    if (end === dot) end--;
    return fixed.slice(0, end + 1);
}

function clampVhsNumber(value, options, integer) {
    let result = Number(value);
    if (!Number.isFinite(result)) result = options.default ?? 0;
    if (options.min != null) result = Math.max(options.min, result);
    if (options.max != null) result = Math.min(options.max, result);
    if (integer) {
        const step = options.step ?? 1;
        const offset = options.mod ?? 0;
        result = Math.round((result - offset) / step) * step + offset;
    } else if (options.round) {
        result = Math.round((result + Number.EPSILON) / options.round) * options.round;
    }
    return result;
}

function drawVhsNumber(ctx, node, widgetWidth, y, height) {
    const margin = 15;
    const showText = LiteGraph.vueNodesMode || app.canvas.ds.scale >= (app.canvas.low_quality_zoom_threshold ?? 0.5);

    ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
    ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
    ctx.beginPath();
    if (showText) {
        ctx.roundRect(margin, y, widgetWidth - margin * 2, height, [height * 0.5]);
    } else {
        ctx.rect(margin, y, widgetWidth - margin * 2, height);
    }
    ctx.fill();

    if (!showText) return;
    if (!this.disabled) ctx.stroke();

    ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
    if (!this.disabled) {
        ctx.beginPath();
        ctx.moveTo(margin + 16, y + 5);
        ctx.lineTo(margin + 6, y + height * 0.5);
        ctx.lineTo(margin + 16, y + height - 5);
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(widgetWidth - margin - 16, y + 5);
        ctx.lineTo(widgetWidth - margin - 6, y + height * 0.5);
        ctx.lineTo(widgetWidth - margin - 16, y + height - 5);
        ctx.fill();
    }

    ctx.textAlign = "left";
    ctx.fillStyle = LiteGraph.WIDGET_SECONDARY_TEXT_COLOR;
    ctx.fillText(this.label || this.name, margin * 2 + 5, y + height * 0.7);

    ctx.textAlign = "right";
    ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
    ctx.fillText(this.displayValue(), widgetWidth - margin * 2 - 20, y + height * 0.7);
}

function setVhsNumberValue(widget, node, value) {
    widget.callback(value);
    node.graph?.setDirtyCanvas(true);
}

function mouseVhsNumber(event, [x], node) {
    const widgetWidth = this.width || node.size[0];
    const margin = 15;
    const step = this.options.step || 1;
    let direction = 0;

    if (x > margin + 6 && x < margin + 16) {
        direction = -1;
    } else if (x > widgetWidth - margin - 16 && x < widgetWidth - margin - 6) {
        direction = 1;
    }

    if (event.type === "pointermove" && event.deltaX) {
        setVhsNumberValue(this, node, this.value + event.deltaX * step);
    } else if (event.type === "pointerdown" && direction) {
        setVhsNumberValue(this, node, this.value + direction * step);
    } else if (event.type === "pointerup" && event.click_time < 200 && !direction) {
        const dialog = app.canvas.prompt(
            "Value",
            this.value,
            (value) => setVhsNumberValue(this, node, value),
            event
        );
        const input = dialog?.querySelector?.(".value");
        input?.addEventListener("keydown", (keyEvent) => {
            if (keyEvent.key !== "Tab") return;
            keyEvent.preventDefault();
            setVhsNumberValue(this, node, input.value);
            dialog.close();
        });
    }
    return true;
}

function createVhsNumberWidget(node, inputName, inputData, integer) {
    const options = Object.assign({}, inputData?.[1] ?? {});
    const widget = {
        name: inputName,
        type: integer ? "VHSINT" : "VHSFLOAT",
        value: options.default ?? 0,
        options,
        config: inputData,
        draw: drawVhsNumber,
        mouse: mouseVhsNumber,
        computeSize(width) {
            return [width, 20];
        },
        callback(value) {
            this.value = clampVhsNumber(value, this.options, integer);
        },
        displayValue() {
            if (integer) return String(this.value | 0);
            return roundVhsNumber(this.value, this.options.precision ?? 3);
        },
    };
    (node.widgets ??= []).push(widget);
    return widget;
}

function useKVState(nodeType) {
    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        chainCallback(this, "onConfigure", function (info) {
            if (!this.widgets || !info || info.widgets_values == null) return;
            let widgetDict = info.widgets_values;

            if (Array.isArray(info.widgets_values)) {
                const convList = convDict[this.type] ?? [];
                widgetDict = {};
                const count = Math.min(info.widgets_values.length, convList.length);
                for (let index = 0; index < count; index++) {
                    const name = convList[index];
                    if (name) widgetDict[name] = info.widgets_values[index];
                }
            }

            if (widgetDict.videopreview?.params?.force_size) {
                delete widgetDict.videopreview.params.force_size;
            }

            const inputs = {};
            for (const input of this.inputs ?? []) {
                inputs[input.name] = input;
            }

            for (const widget of this.widgets) {
                if (widget.type === "button") continue;
                if (Object.prototype.hasOwnProperty.call(widgetDict, widget.name)) {
                    widget.value = widgetDict[widget.name];
                    widget.callback?.(widget.value);
                } else {
                    const nodeTypeInfo = LiteGraph.getNodeType(this.type) || LiteGraph.registered_node_types?.[this.type];
                    const nodeInputs = nodeTypeInfo?.nodeData?.input;
                    let initialValue = null;

                    if (nodeInputs?.required && Object.prototype.hasOwnProperty.call(nodeInputs.required, widget.name)) {
                        const config = nodeInputs.required[widget.name];
                        if (config[1] && Object.prototype.hasOwnProperty.call(config[1], "default")) {
                            initialValue = config[1].default;
                        } else if (config[0]?.length) {
                            initialValue = config[0][0];
                        }
                    } else if (nodeInputs?.optional && Object.prototype.hasOwnProperty.call(nodeInputs.optional, widget.name)) {
                        const config = nodeInputs.optional[widget.name];
                        if (config[1] && Object.prototype.hasOwnProperty.call(config[1], "default")) {
                            initialValue = config[1].default;
                        } else if (config[0]?.length) {
                            initialValue = config[0][0];
                        }
                    }

                    if (initialValue !== null) {
                        widget.value = initialValue;
                        widget.callback?.(widget.value);
                    }
                }

                if (widget.name in inputs && widget.config) {
                    setWidgetConfig(inputs[widget.name], widget.config);
                }
            }
        });

        chainCallback(this, "onSerialize", function (info) {
            info.widgets_values = {};
            if (!this.widgets) return;
            for (const widget of this.widgets) {
                info.widgets_values[widget.name] = widget.value;
            }
        });
    });
}

function useVhsNodeBehavior(nodeType, nodeData) {
    for (const input of Object.values({ ...nodeData.input?.required, ...nodeData.input?.optional })) {
        if (["INT", "FLOAT"].includes(input[0])) {
            input[1] ??= {};
            input[1].widgetType = input[1].widgetType ?? `VHS${input[0]}`;
        }
    }

    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        const originalAddInput = this.addInput;
        this.addInput = function (name, type, options) {
            if (options?.widget) {
                const widget = this.widgets.find((item) => item.name === name);
                if (widget?.config) {
                    type = widget.config[0];
                    if (type === "FLOAT") type = "FLOAT,INT";
                    setWidgetConfig(options, widget.config);
                }
            }
            return originalAddInput.apply(this, [name, type, options]);
        };
    });
}

function fitHeight(node) {
    node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]]);
    node.graph?.setDirtyCanvas(true);
}

function allowDragFromWidget(widget) {
    widget.onPointerDown = function (pointer, node) {
        pointer.onDragStart = () => {
            app.canvas.emitBeforeChange();
            app.canvas.graph?.beforeChange();
            app.canvas.processSelect(node, pointer.eDown, true);
            app.canvas.isDragging = true;
        };
        pointer.onDragEnd = () => {
            app.canvas.isDragging = false;
            app.canvas.graph?.afterChange();
            app.canvas.emitAfterChange();
            app.canvas.dirty_canvas = true;
            app.canvas.dirty_bgcanvas = true;
        };
        app.canvas.dirty_canvas = true;
        return true;
    };
}

function addDateFormatting(nodeType, field) {
    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        const widget = this.widgets.find((item) => item.name === field);
        if (widget) {
            widget.serializeValue = () => applyTextReplacements(app, widget.value);
        }
    });
}

function addVideoPreview(nodeType) {
    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        const previewNode = this;
        const element = document.createElement("div");

        const previewWidget = this.addDOMWidget("videopreview", "preview", element, {
            serialize: false,
            hideOnZoom: false,
            getValue() {
                return element.value;
            },
            setValue(value) {
                element.value = value;
            },
        });

        allowDragFromWidget(previewWidget);

        previewWidget.computeSize = function (width) {
            if (this.aspectRatio && !this.parentEl.hidden) {
                let height = (previewNode.size[0] - 20) / this.aspectRatio + 10;
                if (!(height > 0)) height = 0;
                this.computedHeight = height + 10;
                return [width, height];
            }
            return [width, -4];
        };

        element.style.width = "100%";
        previewWidget.value = { hidden: false, paused: false, params: {}, muted: true };
        
        previewWidget.parentEl = document.createElement("div");
        previewWidget.parentEl.className = "vhs_preview";
        previewWidget.parentEl.style.width = "100%";
        previewWidget.parentEl.style.position = "relative";
        element.appendChild(previewWidget.parentEl);

        previewWidget.videoEl = document.createElement("video");
        previewWidget.videoEl.controls = false;
        previewWidget.videoEl.loop = true;
        previewWidget.videoEl.muted = true;
        previewWidget.videoEl.style.width = "100%";
        previewWidget.videoEl.style.display = "block";
        previewWidget.videoEl.style.cursor = "pointer";

        // =====================================================================
        // 【精致胶囊按钮】：默认隐藏不抢占空间，仅在画面展开时位于左下角
        // =====================================================================
        const playBtn = document.createElement("button");
        playBtn.textContent = "⏸ 暂停";
        playBtn.style.position = "absolute";
        playBtn.style.bottom = "8px";
        playBtn.style.left = "8px";
        playBtn.style.padding = "3px 8px";
        playBtn.style.fontSize = "11px";
        playBtn.style.color = "#ffffff";
        playBtn.style.backgroundColor = "rgba(0, 0, 0, 0.65)";
        playBtn.style.border = "1px solid rgba(255, 255, 255, 0.35)";
        playBtn.style.borderRadius = "10px";
        playBtn.style.cursor = "pointer";
        playBtn.style.zIndex = "99";
        playBtn.style.opacity = "0";
        playBtn.style.display = "none"; // 初始彻底隐藏，绝不漂移到标题栏
        playBtn.style.transition = "opacity 0.2s ease";
        playBtn.style.pointerEvents = "auto";

        const onMetadataLoaded = () => {
            if (previewWidget.videoEl.videoWidth && previewWidget.videoEl.videoHeight) {
                previewWidget.aspectRatio = previewWidget.videoEl.videoWidth / previewWidget.videoEl.videoHeight;
                fitHeight(previewNode);
                // 只有视频画面真正准备好后，才允许胶囊按钮出现
                playBtn.style.display = "block";
            }
        };

        previewWidget.videoEl.addEventListener("loadedmetadata", onMetadataLoaded);
        previewWidget.videoEl.addEventListener("loadeddata", onMetadataLoaded);

        previewWidget.videoEl.addEventListener("error", () => {
            previewWidget.parentEl.hidden = true;
            playBtn.style.display = "none";
            fitHeight(previewNode);
        });

        // 鼠标悬停出声 + 浮现胶囊
        previewWidget.parentEl.onmouseenter = () => {
            previewWidget.videoEl.muted = false;
            if (previewWidget.videoEl.src && previewWidget.videoEl.videoWidth > 0) {
                playBtn.style.display = "block";
                playBtn.style.opacity = "1";
            }
        };

        // 鼠标移出静音 + 胶囊淡出（暂停时保留半透明微显提示）
        previewWidget.parentEl.onmouseleave = () => {
            previewWidget.videoEl.muted = true;
            if (playBtn.style.display !== "none") {
                playBtn.style.opacity = previewWidget.videoEl.paused ? "0.8" : "0";
            }
        };

        // 统一的播放/暂停动作
        const togglePlay = (e) => {
            if (e) {
                e.stopPropagation();
                e.preventDefault();
            }
            if (previewWidget.videoEl.paused) {
                previewWidget.videoEl.play().catch(() => {});
                previewWidget.value.paused = false;
                playBtn.textContent = "⏸ 暂停";
                playBtn.style.backgroundColor = "rgba(0, 0, 0, 0.65)";
            } else {
                previewWidget.videoEl.pause();
                previewWidget.value.paused = true;
                playBtn.textContent = "▶ 播放";
                playBtn.style.backgroundColor = "rgba(0, 120, 255, 0.75)";
                playBtn.style.opacity = "1";
            }
        };

        playBtn.onclick = togglePlay;
        playBtn.onpointerdown = (e) => e.stopPropagation();

        // 视频画面双击或单击也能切换
        previewWidget.videoEl.ondblclick = togglePlay;
        previewWidget.videoEl.onclick = togglePlay;

        previewWidget.parentEl.appendChild(previewWidget.videoEl);
        previewWidget.parentEl.appendChild(playBtn);

        let timeout = null;
        previewNode.updateParameters = (params, forceUpdate) => {
            if (!previewWidget.value || typeof previewWidget.value !== "object") {
                previewWidget.value = {};
            }
            if (!previewWidget.value.params) {
                previewWidget.value.params = {};
            }

            const changed = Object.entries(params).some(([key, value]) => previewWidget.value.params[key] !== value);
            if (!changed) return;

            Object.assign(previewWidget.value.params, params);
            if (!forceUpdate && app.ui.settings.getSettingValue("VHS.AdvancedPreviews") === "Never") {
                return;
            }

            if (timeout) clearTimeout(timeout);
            if (forceUpdate) {
                previewWidget.updateSource();
            } else {
                timeout = setTimeout(() => previewWidget.updateSource(), 100);
            }
        };

        previewWidget.updateSource = function () {
            const params = this.value?.params;
            if (!params) return;

            const query = { ...params, timestamp: Date.now() };
            const format = query.format || "";
            if (format.startsWith("video/") || format === "folder") {
                this.parentEl.hidden = this.value.hidden;
                this.value.paused = false;
                playBtn.textContent = "⏸ 暂停";
                playBtn.style.backgroundColor = "rgba(0, 0, 0, 0.65)";
                this.videoEl.autoplay = !this.value.hidden;
                this.videoEl.src = api.apiURL(`/view?${new URLSearchParams(query)}`);
                this.videoEl.hidden = false;
            }
            this.doQuery?.();
        };

        previewWidget.doQuery = async function () {
            const params = this.value?.params;
            if (!params?.filename) return;
            try {
                const response = await fetch(api.apiURL(`/feihou-vhs/queryvideo?${new URLSearchParams(params)}`));
                previewNode.video_query = await response.json();
            } catch (_) {}
        };

        previewWidget.callback = previewWidget.updateSource;
    });
}

function addFormatWidgets(nodeType) {
    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        // 保底补回 frame_rate 控件（如果丢失）
        let frWidget = this.widgets?.find(w => w.name === "frame_rate");
        if (!frWidget) {
            const nodeTypeInfo = LiteGraph.getNodeType(this.type) || LiteGraph.registered_node_types?.[this.type];
            const frConfig = nodeTypeInfo?.nodeData?.input?.required?.frame_rate || ["FLOAT", { default: 16.0, min: 1.0, step: 1.0 }];
            frWidget = createVhsNumberWidget(this, "frame_rate", frConfig, false);
            const curIdx = this.widgets.indexOf(frWidget);
            if (curIdx > 0) {
                this.widgets.splice(curIdx, 1);
                this.widgets.unshift(frWidget);
            }
        }

        const formatWidget = this.widgets?.find((item) => item.name === "format");
        if (!formatWidget) return;

        let formatWidgetsCount = 0;

        const updateFormatDefinitions = (value) => {
            const nodeTypeInfo = LiteGraph.getNodeType(this.type) || LiteGraph.registered_node_types?.[this.type];
            const nodeInputs = nodeTypeInfo?.nodeData?.input;
            const formats = (nodeInputs?.required?.format ?? nodeInputs?.optional?.format)?.[1]?.formats;
            const definitions = formats?.[value] ?? [];
            const newWidgets = [];

            for (const definition of definitions) {
                let type = definition[2]?.widgetType ?? definition[1];
                if (Array.isArray(type)) type = "COMBO";
                if (!app.widgets[type]) continue;

                app.widgets[type](this, definition[0], definition.slice(1), app);
                const widget = this.widgets.pop();
                widget.config = definition.slice(1);
                newWidgets.push(widget);
            }

            const currentFormatIndex = this.widgets.findIndex((item) => item.name === "format");
            if (currentFormatIndex === -1) return;
            const insertIndex = currentFormatIndex + 1;

            const removed = this.widgets.splice(insertIndex, formatWidgetsCount, ...newWidgets);
            const newNames = new Set(newWidgets.map((widget) => widget.name));

            for (const widget of removed) {
                widget?.onRemove?.();
                if (newNames.has(widget?.name)) continue;
                const slot = this.inputs?.findIndex((input) => input.name === widget?.name);
                if (slot >= 0) this.removeInput(slot);
            }

            for (const widget of newWidgets) {
                const existingInput = this.inputs?.find((input) => input.name === widget.name);
                if (existingInput) {
                    setWidgetConfig(existingInput, widget.config);
                } else {
                    this.addInput(widget.name, widget.config[0], { widget: { name: widget.name } });
                }
            }

            fitHeight(this);
            formatWidgetsCount = newWidgets.length;
        };

        chainCallback(formatWidget, "callback", (value) => {
            updateFormatDefinitions(value);
        });

        if (formatWidget.value) {
            updateFormatDefinitions(formatWidget.value);
        }
    });
}

function addPreviewOptions(nodeType) {
    chainCallback(nodeType.prototype, "getExtraMenuOptions", function (_, options) {
        const previewWidget = this.widgets?.find((widget) => widget.name === "videopreview");
        if (!previewWidget) return;

        const fullpath = previewWidget.value?.params?.fullpath;
        if (fullpath) {
            options.unshift({
                content: "Copy output filepath",
                callback: async () => {
                    await navigator.clipboard.writeText(fullpath);
                },
            });
        }
    });
}

function addVAEInputToggle(nodeType) {
    chainCallback(nodeType.prototype, "onNodeCreated", function () {
        this.reject_ue_connection = (input) => input?.name === "vae";
    });

    chainCallback(nodeType.prototype, "onConnectionsChange", function (contype, slot, iscon, linkInfo) {
        if (contype !== LiteGraph.INPUT || slot !== 3 || !this.inputs?.[3] || this.inputs[3].type !== "VAE") {
            return;
        }

        if (iscon && linkInfo) {
            if (this.inputs[0].type === "IMAGE") this.disconnectInput(0);
            this.inputs[0].type = "LATENT";
        } else {
            if (this.inputs[0].type === "LATENT") this.disconnectInput(0);
            this.inputs[0].type = "IMAGE";
        }
    });
}

app.registerExtension({
    name: "Trucy.VideoCombine",

    getCustomWidgets() {
        return {
            VHSFLOAT(node, inputName, inputData) {
                return createVhsNumberWidget(node, inputName, inputData, false);
            },
            VHSINT(node, inputName, inputData) {
                return createVhsNumberWidget(node, inputName, inputData, true);
            },
        };
    },

    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== NODE_NAME) {
            return;
        }

        if (!nodeData.output) {
            nodeData.output = ["VHS_FILENAMES", "STRING"];
        }
        if (!nodeData.output_name) {
            nodeData.output_name = ["video", "filepath"];
        }
        if (!nodeData.output_is_list) {
            nodeData.output_is_list = [false, false];
        }

        useKVState(nodeType);
        useVhsNodeBehavior(nodeType, nodeData);
        addDateFormatting(nodeType, "filename_prefix");
        addVideoPreview(nodeType);
        addPreviewOptions(nodeType);
        addFormatWidgets(nodeType);
        addVAEInputToggle(nodeType);

        chainCallback(nodeType.prototype, "onNodeCreated", function () {
            if (!this.outputs || this.outputs.length === 0) {
                this.outputs = [
                    { name: "video", type: "VHS_FILENAMES", links: null },
                    { name: "filepath", type: "STRING", links: null }
                ];
            }
        });

        chainCallback(nodeType.prototype, "onExecuted", function (message) {
            if (message?.gifs?.[0]) {
                this.updateParameters(message.gifs[0], true);
            }
        });
    },
});