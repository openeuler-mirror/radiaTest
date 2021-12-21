<template>
    <div 
        class="circle-button"
        ref = "button" 
        @mouseenter="handleHover"
        @mouseleave="handleLeave"
        @mousedown="handleClick"
        @animationend="killAnimation"
        :style="{
            fontSize: size*2.2+'px',
            width: size*3+'px',
            height: size*3+'px',
            lineHeight: size*3+'px',
            fontWeight: fontWeight,
        }"
    >
        <p ref="text" class="text">
            <slot></slot>
        </p>
    </div>
</template>

<script>
import { ref,computed,defineComponent } from 'vue'

export default defineComponent({
    props: {
        align: {
            type: String,
            default: "center"
        },
        size: {
            type: Number,
            default: 10
        },
        color: {
            type: String,
            default: "white"
        },
        backgroundColor: {
            type: String,
            default: "black"
        },
        fontWeight: {
            type: String,
            default: "1000"
        }
    },
    setup(props,context) {
        const button = ref(null)
        const text = ref(null)

        return {
            button,
            text,
            handleHover() {
                button.value.style.borderColor = computed(() => props.backgroundColor).value 
                text.value.style.color = computed(() => props.backgroundColor).value 
                button.value.style.boxShadow = "0 2px 5px " + computed(() => props.backgroundColor).value 
                context.emit('hover') 
            },
            handleLeave() {
                button.value.style.borderColor = "rgb(194,194,194,1)"
                text.value.style.color = "black"
                button.value.style.boxShadow = ""
                context.emit('leave')
            },
            handleClick() {
                if (computed(() => props.backgroundColor).value === "red") {
                    button.value.style.animation = "redclick 0.5s ease-out"
                    new Promise(() => {
                        setTimeout(() => {
                            window.open('https://gitee.com/openeuler/','__self')
                        },800)
                    })
                } else if (computed(() => props.backgroundColor).value === "rgb(26,133,185,1)"){
                    button.value.style.animation = "blueclick 0.5s ease-out"
                    new Promise(() => {
                        setTimeout(() => {
                            window.open('https://openeuler.org/zh/','__self')
                        },800)
                    })
                } else if (computed(() => props.backgroundColor).value === "pink") {
                    button.value.style.animation = "pinkclick 0.5s ease-out"
                    new Promise(() => {
                        setTimeout(() => {
                            window.open('https://space.bilibili.com/527064077?from=search&seid=68416753293712093','__self')
                        },800)
                    })
                }
            },
            killAnimation() {
                button.value.style.animation = ""
            }
        }
    },
})
</script>

<style scoped>
.text {
    position: absolute;
    left: 0;
    top: 0;
    color: black;
    margin: 0 0;
    text-align: center;
    width: 100%;
    transition: all 0.4s ease-in;
}
.circle-button {
    display: inline-block;
    position: relative;
    border-radius: 100%;
    border-style: solid;
    border-color: rgb(194,194,194,1);
    transition: all 0.4s ease-in;
}
.circle-button:hover {
    cursor: pointer;
}
</style>
<style>
@keyframes redclick {
    0% {
        box-shadow: 0 2px 5px red;
    }
    50% {
        box-shadow: 0 0 0;
    }
    100% {
        box-shadow: 0 2px 5px red;
    }
}
@keyframes blueclick {
    0% {
        box-shadow: 0 2px 5px rgb(26,133,185,1);
    }
    50% {
        box-shadow: 0 0 0;
    }
    100% {
        box-shadow: 0 2px 5px rgb(26,133,185,1);
    }
}
@keyframes pinkclick {
    0% {
        box-shadow: 0 2px 5px pink;
    }
    50% {
        box-shadow: 0 0 0;
    }
    100% {
        box-shadow: 0 2px 5px pink;
    }
}
</style>