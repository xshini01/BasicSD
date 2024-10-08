import gradio as gr
import time
import torch
import matplotlib.pyplot as plt
from PIL import Image
from peft import LoraModel, LoraConfig
from IPython.display import clear_output, display, Javascript, Markdown
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler, StableDiffusionXLPipeline
from transformers import CLIPTextModel, CLIPTokenizer, AutoTokenizer, AutoModelForCausalLM
from compel import Compel, ReturnedEmbeddingsType

def load_model(model_id, lora_id, btn_ceck, progress=gr.Progress()):
    model_id_lower = model_id.lower()
    if "sd-xl" in model_id_lower or "sdxl" in model_id_lower or "xl" in model_id_lower:
        gr.Info("wait a minute the model is loading!")
        progress(0.2, desc="Starting model loading")
        time.sleep(1)
        pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    else:
        gr.Info("wait a minute the model is loading!")
        progress(0.2, desc="Starting model loading")
        pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)

    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

    if lora_id:
        try:
            gr.Info("wait a minute the Lora is loading!")
            progress(0.5, desc="Load LoRA weight")
            pipe.load_lora_weights(lora_id, adapter_name=lora_id)
            pipe.fuse_lora(lora_scale=0.7)
            clear_output()
            gr.Info(f"Load LoRA {lora_id} Success")
        except Exception as e:
            clear_output()
            gr.Info(f"LoRA {lora_id} not compatible with model {model_id}")
            gr.Info(f"Use another Lora, if sdxl model use Lora xl")
            gr.Info(f"Load Model without Lora")
    else:
        clear_output()


    pipe = pipe.to("cuda")
    gr.Info(f"Load Model {model_id} and {lora_id} Success")
    progress(1, desc="Model loaded successfully")
    generate_imgs = gr.Button(interactive=True)
    generated_imgs_with_tags = gr.Button()
    if btn_ceck :
        generated_imgs_with_tags = gr.Button(interactive=True)
    return pipe, model_id, lora_id, generate_imgs, generated_imgs_with_tags


def generated_imgs_tags(copyright_tags, character_tags, general_tags, rating, aspect_ratio_tags, Length_prompt, pipe):
    MODEL_NAME = "p1atdev/dart-v2-moe-sft"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.bfloat16)
    prompt_template = (
    f"<|bos|>"
    f"<copyright>{copyright_tags}</copyright>"
    f"<character>{character_tags}</character>"
    f"<|rating:{rating}|><|aspect_ratio:{aspect_ratio_tags}|><|length:{Length_prompt}|>"
    f"<general>{general_tags}<|identity:none|><|input_end|>"
    )
    inputs = tokenizer(prompt_template, return_tensors="pt").input_ids

    with torch.no_grad():
        outputs = model.generate(
        inputs,
        do_sample=True,
        temperature=1.0,
        top_p=1.0,
        top_k=100,
        max_new_tokens=128,
        num_beams=1,
        )

    generated_text = ", ".join([tag for tag in tokenizer.batch_decode(outputs[0], skip_special_tokens=True) if tag.strip() != ""])
    copy = gr.Button(interactive=True)
    tags_imgs = gr.Button()
    btn_ceck = generated_text
    if pipe:
      tags_imgs = gr.Button(interactive=True)
    return generated_text, copy, tags_imgs, btn_ceck

def gradio_copy_text(_text: None):
    gr.Info("Copied!")


COPY_ACTION_JS = """\
(inputs, _outputs) => {
if (inputs.trim() !== "") {
    navigator.clipboard.writeText(inputs);
}
}"""

all_images = []
def generated_imgs(model_id, prompt, negative_prompt, width, height, steps, scale, clip_skip, num_images,pipe):
    all_images = []
    model_id_lower = model_id.lower()

    for _ in range(num_images):
        if "sd-xl" in model_id_lower or "sdxl" in model_id_lower or "xl" in model_id_lower:
            compel = Compel(
                tokenizer=[pipe.tokenizer, pipe.tokenizer_2],
                text_encoder=[pipe.text_encoder, pipe.text_encoder_2],
                returned_embeddings_type=ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED,
                requires_pooled=[False, True]
            )
            conditioning, pooled = compel(prompt)
            image = pipe(prompt_embeds=conditioning, pooled_prompt_embeds=pooled, height=height, num_inference_steps=steps, width=width,
                        negative_prompt=negative_prompt, guidance_scale=scale, clip_skip=clip_skip).images[0]
        else:
            compel = Compel(tokenizer=pipe.tokenizer, text_encoder=pipe.text_encoder)
            embeds = compel(prompt)
            image = pipe(prompt_embeds=embeds, height=height, num_inference_steps=steps, width=width,
                    negative_prompt=negative_prompt, guidance_scale=scale, clip_skip=clip_skip).images[0]
        image_path = f"output_image_{len(all_images) + 1}.png"
        image.save(image_path)
        all_images.append(image_path)
    return all_images

model_id = "John6666/anima-pencil-xl-v5-sdxl"
lora_id = "xshini/Nakano_Miku_xl"

copyright_tags= "Go-Toubun no Hanayome"
character_tags = "nakano miku"
general_tags = "1girl, solo"
rating = "general"
aspect_ratio_tags = "square"
Length_prompt= "short"

prompt = "1girl, solo, nakano miku, solo, green skirt, headphones around neck, looking at viewer, blush, closed mouth, white shirt, long sleeves, blue cardigan, pleated skirt, black pantyhose"
negative_prompt = "NSFW, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name,"
width = 1024
height = 1024
steps = 20
scale = 7
clip_skip= 2
num_images = 1

with gr.Blocks(theme='JohnSmith9982/small_and_pretty') as ui:
    with gr.Row():
        gr.Markdown(
            """
            # **Basic Stable Diffusion**

            ***support SDXL model (beta)***

            **by Xshini/KZR**
            """
        )

    with gr.Row(show_progress=True, variant="panel" ):
        model_id_input = gr.Dropdown(choices=["stablediffusionapi/abyssorangemix3a1b","Ojimi/anime-kawai-diffusion","Linaqruf/anything-v3-1","circulus/canvers-anime-v3.8.1","redstonehero/cetusmix_v4","DGSpitzer/Cyberpunk-Anime-Diffusion","dreamlike-art/dreamlike-anime-1.0","Lykon/dreamshaper-8","emilianJR/majicMIX_realistic_v6","Meina/MeinaMix_V11","Meina/MeinaPastel_V7","jzli/RealCartoon3D-v11","Meina/MeinaUnreal_V5","redstonehero/xxmix_9realistic_v40","stablediffusionapi/yesmix-v35","Lykon/AAM_AnyLora_AnimeMix","Lykon/AnyLoRA","xshini/pooribumix_V1","John6666/anima-pencil-sdxl","GraydientPlatformAPI/perfectpony-xl","cagliostrolab/animagine-xl-3.1","John6666/anima-pencil-xl-v5-sdxl"],label="Model ID", value=model_id, allow_custom_value=True)
        lora_id_input = gr.Dropdown(choices=["xshini/KizunaAi","xshini/NakanoMiku","xshini/HiguchiKaede","xshini/tokisaki-Kurumi-XL"],label="LoRA ID", value=lora_id, allow_custom_value=True)
        with gr.Column():
            load_model_btn = gr.Button("Load Model", variant="primary", size='lg')
            toggle_dark = gr.Button(value="Toggle Dark", size='lg')
            toggle_dark.click(
                None,
                js="""
                () => {
                    document.body.classList.toggle('dark');
                }
                """,
            )


    with gr.Row():
        with gr.Column(variant ='panel'):
            copyright_tags_input = gr.Textbox(label="Copyright Tags", value=copyright_tags, lines=2)
            character_tags_input = gr.Textbox(label="Character Tags", value=character_tags, lines=2)
            general_tags_input = gr.Textbox(label="General Tags", value=general_tags, lines=2)
            rating_input = gr.Radio(["sfw","general","sensitive"], label="Rating", value=rating)
            aspect_ratio_tags_input = gr.Radio(["ultra_wide","wide","square", "tall", "ultra_tall"], label="Aspect Ratio", value=aspect_ratio_tags)
            Length_prompt_input = gr.Radio(["very_short","short","medium", "long", "very_long"], label="Length Prompt", value=Length_prompt)
        with gr.Column(variant ='panel'):
            generated_imgs_tags_btn = gr.Button("Generate Prompt", variant="primary")
            with gr.Group():
                prompt_output = gr.Textbox(label="Generate Prompt", info="this is an optional feature, you can directly generate images in ''Advanced Prompt Images''", lines=3, value="", interactive=False)
                clipboard_btn = gr.Button(value="Copy to clipboard", interactive=False,)
            generated_imgs_with_tags_btn = gr.Button(value="Generate image with this prompt!",variant='primary', interactive=False)

            with gr.Accordion(label="Advanced Prompt Images", open=False):
                prompt_input = gr.Textbox(label="Prompt", value=prompt, lines=5)
                negative_prompt_input = gr.Textbox(label="Negative Prompt", value=negative_prompt, lines=3)
                width_input = gr.Slider(minimum=256, maximum=2048, step=64, label="Width", value=width)
                height_input = gr.Slider(minimum=256, maximum=2048, step=64, label="Height", value=height)
                steps_input = gr.Slider(minimum=1, maximum=50, step=1, label="Steps", value=steps)
                scale_input = gr.Slider(minimum=1, maximum=20, step=0.5, label="Scale", value=scale)
                clip_skip_input = gr.Slider(minimum=1, maximum=12, step=1, label="Clip Skip", value=clip_skip)
                num_images_input = gr.Slider(minimum=1, maximum=5, step=1, label="Number of Images", value=num_images)
                generated_imgs_btn = gr.Button("Generate Images", variant="primary", interactive=False)
            image_output = gr.Gallery(label="Generated Image",show_label=False,columns=[2], rows=[2], object_fit="contain", height="auto")

    pipe = gr.State()
    btn_ceck = gr.State()
    load_model_btn.click(load_model, inputs=[model_id_input, lora_id_input, btn_ceck], outputs=[pipe, model_id_input, lora_id_input, generated_imgs_btn, generated_imgs_with_tags_btn])
    generated_imgs_tags_btn.click(generated_imgs_tags, inputs=[copyright_tags_input, character_tags_input, general_tags_input, rating_input, aspect_ratio_tags_input, Length_prompt_input, pipe], outputs=[prompt_output,clipboard_btn, generated_imgs_with_tags_btn, btn_ceck])
    clipboard_btn.click(gradio_copy_text, inputs=prompt_output, js=COPY_ACTION_JS)
    generated_imgs_with_tags_btn.click(generated_imgs, inputs=[model_id_input, prompt_output, negative_prompt_input, width_input, height_input, steps_input, scale_input, clip_skip_input, num_images_input,pipe], outputs=image_output)
    generated_imgs_btn.click(generated_imgs, inputs=[model_id_input, prompt_input, negative_prompt_input, width_input, height_input, steps_input, scale_input, clip_skip_input, num_images_input,pipe], outputs=image_output)

ui.queue()
ui.launch(share=True, debug=True, inline=False)

if __name__ == "__main__":
    ui.launch()
