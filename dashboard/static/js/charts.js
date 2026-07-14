function showLoading(){document.getElementById('loading').style.display='flex';}
function hideLoading(){document.getElementById('loading').style.display='none';}

// Chart.js pastel defaults
Chart.defaults.color='#9ca3af';
Chart.defaults.borderColor='rgba(0,0,0,0.04)';
Chart.defaults.font.family="'Inter',sans-serif";
Chart.defaults.font.size=11;
Chart.defaults.font.weight=500;

function createHourlyChart(canvas,predData,actualData,predColor,actualColor){
    const ctx=canvas.getContext('2d');
    const predGrad=ctx.createLinearGradient(0,0,0,280);
    predGrad.addColorStop(0,predColor+'55');
    predGrad.addColorStop(1,predColor+'05');

    return new Chart(canvas,{
        type:'line',
        data:{
            labels:Array.from({length:24},(_,i)=>`${String(i).padStart(2,'0')}:00`),
            datasets:[
                {
                    label:'Predicted',
                    data:predData,
                    borderColor:predColor,
                    backgroundColor:predGrad,
                    borderWidth:3,
                    fill:true,
                    tension:0.4,
                    pointRadius:0,
                    pointHoverRadius:6,
                    pointHoverBackgroundColor:predColor,
                    pointHoverBorderColor:'#fff',
                    pointHoverBorderWidth:3,
                },
                {
                    label:'Actual',
                    data:actualData,
                    borderColor:actualColor,
                    backgroundColor:'transparent',
                    borderWidth:2.5,
                    borderDash:[8,4],
                    fill:false,
                    tension:0.4,
                    pointRadius:0,
                    pointHoverRadius:5,
                    pointHoverBackgroundColor:actualColor,
                    pointHoverBorderColor:'#fff',
                    pointHoverBorderWidth:2,
                }
            ]
        },
        options:{
            responsive:true,
            maintainAspectRatio:true,
            interaction:{mode:'index',intersect:false},
            plugins:{
                legend:{
                    position:'top',
                    labels:{
                        boxWidth:10,boxHeight:10,borderRadius:5,
                        useBorderRadius:true,padding:20,
                        font:{size:12,weight:600},
                        color:'#6b7280',
                    },
                },
                tooltip:{
                    backgroundColor:'#fff',
                    titleColor:'#3a3a3a',
                    bodyColor:'#6b7280',
                    borderColor:'rgba(0,0,0,0.08)',
                    borderWidth:1,
                    cornerRadius:12,
                    padding:14,
                    titleFont:{weight:700},
                    boxWidth:8,boxHeight:8,boxPadding:4,
                    displayColors:true,
                    callbacks:{
                        label:function(ctx){
                            return `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} pax`;
                        }
                    }
                },
            },
            scales:{
                x:{
                    grid:{display:false},
                    ticks:{font:{size:10,weight:500},maxRotation:0,autoSkip:true,maxTicksLimit:12},
                },
                y:{
                    beginAtZero:true,
                    grid:{color:'rgba(0,0,0,0.03)'},
                    ticks:{
                        font:{size:10},
                        callback:function(v){return v>=1000?(v/1000).toFixed(1)+'k':v;}
                    },
                    title:{display:true,text:'Passengers',font:{size:10,weight:600},color:'#9ca3af'},
                },
            }
        }
    });
}

function createLanesChart(canvas,predData,actualData,predColor,actualColor,label){
    return new Chart(canvas,{
        type:'bar',
        data:{
            labels:Array.from({length:24},(_,i)=>`${String(i).padStart(2,'0')}:00`),
            datasets:[
                {
                    label:'Predicted '+label,
                    data:predData,
                    backgroundColor:predColor+'66',
                    borderColor:predColor,
                    borderWidth:1,
                    borderRadius:6,
                    borderSkipped:false,
                    order:2,
                },
                {
                    label:'Actual '+label,
                    data:actualData,
                    type:'line',
                    borderColor:actualColor,
                    backgroundColor:'transparent',
                    borderWidth:2.5,
                    borderDash:[6,3],
                    tension:0.4,
                    pointRadius:3,
                    pointBackgroundColor:actualColor,
                    pointBorderColor:'#fff',
                    pointBorderWidth:2,
                    pointHoverRadius:6,
                    order:1,
                }
            ]
        },
        options:{
            responsive:true,
            maintainAspectRatio:true,
            interaction:{mode:'index',intersect:false},
            plugins:{
                legend:{
                    position:'top',
                    labels:{
                        boxWidth:10,boxHeight:10,borderRadius:5,
                        useBorderRadius:true,padding:20,
                        font:{size:12,weight:600},color:'#6b7280',
                    },
                },
                tooltip:{
                    backgroundColor:'#fff',
                    titleColor:'#3a3a3a',bodyColor:'#6b7280',
                    borderColor:'rgba(0,0,0,0.08)',borderWidth:1,
                    cornerRadius:12,padding:14,
                    titleFont:{weight:700},
                    boxWidth:8,boxHeight:8,boxPadding:4,
                    displayColors:true,
                    callbacks:{
                        label:function(ctx){
                            return `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}`;
                        }
                    }
                },
            },
            scales:{
                x:{
                    grid:{display:false},
                    ticks:{font:{size:10,weight:500},maxRotation:0,autoSkip:true,maxTicksLimit:12},
                },
                y:{
                    beginAtZero:true,
                    grid:{color:'rgba(0,0,0,0.03)'},
                    ticks:{font:{size:10}},
                    title:{display:true,text:label+' Open',font:{size:10,weight:600},color:'#9ca3af'},
                },
            }
        }
    });
}
