"""Fictional preview QA. No USB requests or radio changes."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE='http://127.0.0.1:8771'
CAP={'state':'registered','sim_present':True,'registered':True,'ussd_state':1,
     'can_set_mode':True,'supported_modes':[[8,0],[4,0],[12,8]],'current_mode':[12,8],
     'can_set_roaming':True,'roaming':{'available':True,'allowed':False,'home_locked':True},
     'can_set_bands':True,'saved_bands':'auto','current_bands':[256],
     'band_choices':[{'id':'auto','label':'Tự động'},{'id':'b3','label':'B3 · 1800 MHz'}]}


def main():
    out=Path('runtime/radio-refresh-qa');out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page();errors=[];posts=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('request',lambda request:posts.append(request.url) if request.method=='POST' else None)
        page.route('**/api/modem/status',lambda route:route.fulfill(json=CAP))
        for width in (320,390,768,1280):
            page.set_viewport_size({'width':width,'height':900})
            page.goto(BASE+'/modem/network')
            expect(page.locator('#roaming-allowed')).to_be_enabled()
            page.locator('#band-selection').select_option('b3')
            page.locator('#roaming-allowed').check()
            page.evaluate('''() => {window.savedRead=portalReadTelemetry;
                window.portalReadTelemetry=()=>new Promise(resolve=>window.finishRead=resolve);refresh();}''')
            expect(page.locator('#radio-mode')).to_be_enabled()
            expect(page.locator('#roaming-allowed')).to_be_enabled()
            page.evaluate('(sample)=>finishRead(sample)',CAP)
            expect(page.locator('#band-selection')).to_have_value('b3')
            expect(page.locator('#roaming-allowed')).to_be_checked()
            assert page.evaluate('document.body.scrollWidth<=innerWidth'),width
            page.screenshot(path=str(out/f'network-{width}.png'),full_page=True)
        page.goto(BASE+'/overview')
        expect(page.locator('#quick-ap')).to_be_enabled()
        page.evaluate("() => {window.portalReadTelemetry=async()=>{throw Error('fixture read failure')}}")
        page.locator('#quick-refresh').click()
        expect(page.locator('#quick-notice')).to_contain_text('vẫn có thể chọn')
        expect(page.locator('#quick-ap')).to_be_enabled()
        page.locator('#quick-ap').click()
        expect(page.locator('#quick-dialog')).to_be_visible()
        assert not posts,posts
        assert not errors,errors
        browser.close()
    print('PASS: 4 layouts; editing during GET; drafts retained; Quick dialog available after failed refresh; zero mutations')


if __name__=='__main__':main()
