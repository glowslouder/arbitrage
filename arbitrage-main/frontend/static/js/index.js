import { getData } from "./api.js"
import { applyTranslation } from "./translation.js"

const reload_interval = 60000
let last_time_reload = 0
let next_time_reload = 0
let data = {}
let sort_ = "funding"

function sorted_data() {
  if (sort_ === "funding") {
    data['coins'].sort((a, b) => {return b.delta-a.delta})
  } else if (sort_ === "spread") {
    data['coins'].sort((a, b) => {return b.spread-a.spread})
  }
  return data
}

async function loadData() {
  try {
    data = await getData()
    last_time_reload = Math.floor(new Date().getTime() / 1000)
    next_time_reload = last_time_reload + Math.floor(reload_interval / 1000)
    document.querySelector("#main_table tbody").innerHTML = sorted_data().coins.map(coin => createRow(coin)).join("")
  } catch(err) {
    console.error(err)
  }
}

function createRow(data) {
  const links = {
    backpack: "https://backpack.exchange/trade/#_USD_PERP",
    kiloex: "https://app.kiloex.io/trade?token=#USD",
    aevo: "https://app.aevo.xyz/perpetual/#",
    paradex: "https://app.paradex.trade/trade/#-USD-PERP"
  }
  const time = {
    backpack: 8,
    kiloex: 1,
    aevo: 1,
    paradex: 8
  }
  return `
  <tr>
      <td class="coin-name" rowspan="2">${data['coin']}</td>
      <td class="pair-cell">
          🟢
          <a href="${links[data['max']['exchange']].replace(/#/, data['coin'])}" class="exchange_link"><img src="static/icon/${data['max']['exchange']}.png" width="20px" height="20px"> ${data['max']['exchange']}</a>
          <p style="margin-left: 15px;">${data['max']['index_price'].toFixed(4)}</p>
      </td>
      <td>
          <p>${data['max']['rate'].toFixed(4)}% <small style="margin-left: 5px ;"> ${time[data['max']['exchange']]}h</small> </p>
      </td>
      <td class="coin-name" rowspan="2">${data['APR'].toFixed(4)}%</td>
      <td class="coin-name" rowspan="2"><span class="badge green">${data['delta'].toFixed(4)}%</span></td>
      <td class="coin-name" rowspan="2"><span class="badge green">${data['spread'].toFixed(4)}%</span></td>
  </tr>
  <tr class="second_tr">
      <!-- порожня перша клітинка, бо rowspan у попередньому -->
      <td class="pair-cell">
          🔴
          <a href="${links[data['min']['exchange']].replace(/#/, data['coin'])}" class="exchange_link"><img src="static/icon/${data['min']['exchange']}.png" width="20px" height="20px"> ${data['min']['exchange']}</a>
          <p style="margin-left: 15px;">${data['min']['index_price'].toFixed(4)}</p>
      </td>
      <td style="border-right: 1px solid var(--border);">
          <p>${data['min']['rate'].toFixed(4)}% <small style="margin-left: 5px ;"> ${time[data['min']['exchange']]}h</small> </p>
      </td>
  </tr>
  `
}

document.addEventListener('DOMContentLoaded', () => {
  const btn   = document.getElementById('exchangeDropdownBtn');
  const panel = document.getElementById('exchangeDropdown');
  const reset = document.getElementById('exchangeReset');
  const apply = document.getElementById('exchangeApply');
  const sort_by = document.getElementById("sort-select");

  // відкриваємо / закриваємо панель
  btn.addEventListener('click', e => {
    e.stopPropagation();
    panel.classList.toggle('show');
  });

  // щоб кліки всередині панелі НЕ закривали дропдаун
  panel.addEventListener('click', e => e.stopPropagation());

  // клік поза дропдауном — ховаємо
  document.addEventListener('click', () => panel.classList.remove('show'));

  // Reset: знімаємо всі галочки
  reset.addEventListener('click', () => {
    panel.querySelectorAll('input[type=\"checkbox\"]').forEach(chk => chk.checked = false);
  });

  // Apply: ховаємо панель (тут можна обробити вибір)
  apply.addEventListener('click', () => {
    panel.classList.remove('show');
    // TODO: обробити вибрані біржі
  });

  sort_by.addEventListener('change', e => {
    switch (e.target.value) {
      case ("long+short: funding"):
        sort_ = "funding"
        break
      case ("long+short: spread"):
        sort_ = "spread"
        break
    }
    document.querySelector("#main_table tbody").innerHTML = sorted_data().coins.map(coin => createRow(coin)).join("")
  })



  applyTranslation()
  loadData()
  setInterval(() => {
    loadData()
  }, reload_interval)
  setInterval(() => {
    let time_remaining = next_time_reload - Math.round(Date.now()/1000)
    document.getElementById("time").innerHTML = time_remaining + "s"
    if (time_remaining <= 0) {
      document.getElementById("time").classList.add("invisible")
      document.getElementById("loader").classList.remove("invisible")
    } else {
      document.getElementById("time").classList.remove("invisible")
      document.getElementById("loader").classList.add("invisible")
    }
  }, 1000)
});
