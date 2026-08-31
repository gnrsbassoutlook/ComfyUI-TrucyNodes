import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { setWidgetConfig } from "../../extensions/core/widgetInputs.js";
import { applyTextReplacements } from "../../scripts/utils.js";

const NODE_NAME = "TrucyVideoCombine";

// 预览最大高度限制（像素），防止竖屏视频撑爆屏幕
const MAX_PREVIEW_HEIGHT = 420;

function chainCallback(object, property, callback) {
  if (object === undefined) return;
  if (property in object && object[property]) {
    const original = object[property];
    object[property] = function () {
      const result = original.apply(this, arguments);
      return callback.apply(this, arguments) ?? result;
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
    "custom_path",
    "format",
    "pingpong",
    "save_output",
  ],
};

function useKVState(nodeType) {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    chainCallback(this, "onConfigure", function (info) {
      if (!this.widgets || typeof info.widgets_values !== "object") return;
      let widgetDict = info.widgets_values;

      if (info.widgets_values.length) {
        const convList = convDict[this.type];
        if (convList && info.widgets_values.length >= convList.length) {
          widgetDict = {};
          for (let index = 0; index < convList.length; index++) {
            if (convList[index]) widgetDict[convList[index]] = info.widgets_values[index];
          }
        }
      }

      if (widgetDict.videopreview?.params?.force_size) {
        delete widgetDict.videopreview.params.force_size;
      }

      const inputs = {};
      for (const input of this.inputs || []) inputs[input.name] = input;

      if (widgetDict.length === undefined) {
        for (const widget of this.widgets) {
          if (widget.type === "button") continue;
          if (widget.name in widgetDict) {
            widget.value = widgetDict[widget.name];
            widget.callback?.(widget.value);
          } else {
            const nodeInputs = LiteGraph.getNodeType(this.type)?.nodeData?.input;
            let initialValue = null;
            if (nodeInputs?.required?.hasOwnProperty(widget.name)) {
              const cfg = nodeInputs.required[widget.name];
              if (cfg[1]?.hasOwnProperty("default")) initialValue = cfg[1].default;
              else if (Array.isArray(cfg[0]) && cfg[0].length) initialValue = cfg[0][0];
            } else if (nodeInputs?.optional?.hasOwnProperty(widget.name)) {
              const cfg = nodeInputs.optional[widget.name];
              if (cfg[1]?.hasOwnProperty("default")) initialValue = cfg[1].default;
              else if (Array.isArray(cfg[0]) && cfg[0].length) initialValue = cfg[0][0];
            }
            if (initialValue !== null && initialValue !== undefined) {
              widget.value = initialValue;
              widget.callback?.(widget.value);
            }
          }
          if (widget.name in inputs && widget.config) {
            setWidgetConfig(inputs[widget.name], widget.config);
          }
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
  const allInputs = { ...nodeData.input?.required, ...nodeData.input?.optional };
  for (const input of Object.values(allInputs)) {
    if (["INT", "FLOAT"].includes(input[0])) {
      input[1] ??= {};
      input[1].widgetType ??= `VHS${input[0]}`;
    }
  }

  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    const originalAddInput = this.addInput;
    this.addInput = function (name, type, options) {
      if (options?.widget) {
        const widget = this.widgets?.find((item) => item.name === name);
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
  const computedHeight = node.computeSize([node.size[0], node.size[1]])[1];
  node.setSize([node.size[0], computedHeight]);
  node.graph?.setDirtyCanvas(true);
}

function addVAEInputToggle(nodeType) {
  chainCallback(nodeType.prototype, "onConnectionsChange", function (contype, slot, isConnected, linkInfo) {
    if (contype !== LiteGraph.INPUT || slot !== 3 || this.inputs?.[3]?.type !== "VAE") return;
    if (isConnected && linkInfo) {
      this.inputs[0].type = "LATENT";
    } else {
      this.inputs[0].type = "IMAGE";
    }
  });
}

function addDateFormatting(nodeType, field) {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    const widget = this.widgets?.find((item) => item.name === field);
    if (widget) {
      widget.serializeValue = () => applyTextReplacements(app, widget.value);
    }
  });
}

// 视频预览功能（加入最大高度限制与居中缩放）
function addVideoPreview(nodeType, isInput = true) {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    const element = document.createElement("div");
    const previewNode = this;

    const previewWidget = this.addDOMWidget("videopreview", "preview", element, {
      serialize: false,
      hideOnZoom: false,
      getValue() { return element.value; },
      setValue(value) { element.value = value; },
    });

    // 计算预览高度：增加 MAX_PREVIEW_HEIGHT 限制
    previewWidget.computeSize = function (width) {
      if (this.aspectRatio && !this.parentEl.hidden) {
        let naturalHeight = (previewNode.size[0] - 20) / this.aspectRatio;
        // 关键：限制高度最大不超过 MAX_PREVIEW_HEIGHT
        let height = Math.min(naturalHeight, MAX_PREVIEW_HEIGHT) + 10;
        if (!(height > 0)) height = 0;
        return [width, height + 10];
      }
      return [width, -4];
    };

    previewWidget.value = {
      hidden: false,
      paused: false,
      params: {},
      muted: false,
    };

    previewWidget.parentEl = document.createElement("div");
    previewWidget.parentEl.className = "vhs_preview";
    previewWidget.parentEl.style.width = "100%";
    previewWidget.parentEl.style.maxHeight = `${MAX_PREVIEW_HEIGHT}px`;
    previewWidget.parentEl.style.display = "flex";
    previewWidget.parentEl.style.justifyContent = "center";
    previewWidget.parentEl.style.alignItems = "center";
    previewWidget.parentEl.style.overflow = "hidden";
    previewWidget.parentEl.style.background = "rgba(0,0,0,0.3)";
    previewWidget.parentEl.style.borderRadius = "4px";
    element.appendChild(previewWidget.parentEl);

    previewWidget.videoEl = document.createElement("video");
    previewWidget.videoEl.controls = false;
    previewWidget.videoEl.loop = true;
    previewWidget.videoEl.autoplay = true;
    previewWidget.videoEl.playsInline = true;
    previewWidget.videoEl.muted = true;
    previewWidget.videoEl.defaultMuted = true;
    previewWidget.videoEl.preload = "auto";

    // 关键样式：高度限制且等比例自适应，不撑破窗口
    previewWidget.videoEl.style.maxWidth = "100%";
    previewWidget.videoEl.style.maxHeight = `${MAX_PREVIEW_HEIGHT}px`;
    previewWidget.videoEl.style.objectFit = "contain";
    previewWidget.videoEl.style.display = "block";

    // 鼠标移入开声
    previewWidget.videoEl.addEventListener("mouseenter", () => {
      previewWidget.videoEl.defaultMuted = false;
      previewWidget.videoEl.muted = false;
      previewWidget.videoEl.volume = 1.0;
      const playPromise = previewWidget.videoEl.play();
      if (playPromise?.catch) playPromise.catch(() => {});
    });

    // 鼠标移出静音
    previewWidget.videoEl.addEventListener("mouseleave", () => {
      previewWidget.videoEl.muted = true;
      previewWidget.videoEl.defaultMuted = true;
    });

    previewWidget.videoEl.addEventListener("loadedmetadata", () => {
      const vw = previewWidget.videoEl.videoWidth;
      const vh = previewWidget.videoEl.videoHeight;
      if (vw > 0 && vh > 0) {
        previewWidget.aspectRatio = vw / vh;
      }
      fitHeight(this);
    });

    previewWidget.videoEl.addEventListener("loadeddata", () => {
      previewWidget.videoEl.muted = true;
      previewWidget.videoEl.defaultMuted = true;
      const playPromise = previewWidget.videoEl.play();
      if (playPromise?.catch) playPromise.catch(() => {});
    });

    previewWidget.videoEl.addEventListener("error", () => {
      previewWidget.parentEl.hidden = true;
      fitHeight(this);
    });

    previewWidget.parentEl.appendChild(previewWidget.videoEl);

    this.updateParameters = (params, forceUpdate) => {
      if (!params) return;
      if (!previewWidget.value.params) previewWidget.value.params = {};
      Object.assign(previewWidget.value.params, params);
      previewWidget.updateSource(forceUpdate);
    };

    previewWidget.updateSource = function (forceUpdate = false) {
      if (!this.value.params?.filename) return;
      const params = {
        ...this.value.params,
        timestamp: Date.now(),
      };
      this.videoEl.muted = true;
      this.videoEl.defaultMuted = true;
      this.videoEl.src = api.apiURL(`/view?${new URLSearchParams(params)}`);
      this.videoEl.autoplay = true;
      this.videoEl.loop = true;
      this.parentEl.hidden = false;
      this.videoEl.load();
      const playPromise = this.videoEl.play();
      if (playPromise?.catch) playPromise.catch(() => {});
      fitHeight(previewNode);
    };
  });
}

function addFormatWidgets(nodeType) {
  chainCallback(nodeType.prototype, "onNodeCreated", function () {
    const formatWidget = this.widgets?.find((w) => w.name === "format");
    if (!formatWidget) return;
    const formatWidgetIndex = this.widgets.indexOf(formatWidget) + 1;
    let formatWidgetsCount = 0;

    chainCallback(formatWidget, "callback", (value) => {
      const formats = LiteGraph.registered_node_types[this.type]?.nodeData?.input?.required?.format?.[1]?.formats;
      const newWidgets = [];
      if (formats?.[value]) {
        for (const definition of formats[value]) {
          let type = definition[2]?.widgetType ?? definition[1];
          if (Array.isArray(type)) type = "COMBO";
          app.widgets[type](this, definition[0], definition.slice(1), app);
          const widget = this.widgets.pop();
          widget.config = definition.slice(1);
          newWidgets.push(widget);
        }
      }
      const removed = this.widgets.splice(formatWidgetIndex, formatWidgetsCount, ...newWidgets);
      const newNames = new Set(newWidgets.map((w) => w.name));
      for (const widget of removed) {
        if (!newNames.has(widget.name)) {
          const slot = this.inputs.findIndex((input) => input.name === widget.name);
          if (slot >= 0) this.removeInput(slot);
        }
      }
      for (const widget of newWidgets) {
        const existingInput = this.inputs.find((input) => input.name === widget.name);
        if (existingInput) {
          setWidgetConfig(existingInput, widget.config);
        } else {
          this.addInput(widget.name, widget.config[0], { widget: { name: widget.name } });
        }
      }
      fitHeight(this);
      formatWidgetsCount = newWidgets.length;
    });
  });
}

app.registerExtension({
  name: "Trucy.VideoCombine",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE_NAME) return;
    useKVState(nodeType);
    useVhsNodeBehavior(nodeType, nodeData);
    addDateFormatting(nodeType, "filename_prefix");
    chainCallback(nodeType.prototype, "onExecuted", function (message) {
      if (message?.gifs?.length && message.gifs[0]) {
        this.updateParameters?.(message.gifs[0], true);
      }
    });
    addVideoPreview(nodeType, false);
    addFormatWidgets(nodeType);
    addVAEInputToggle(nodeType);
  },
});